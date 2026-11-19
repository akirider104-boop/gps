import UIKit
import Capacitor
import Photos
import AVFoundation

class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        guard let windowScene = scene as? UIWindowScene else { return }

        window = UIWindow(windowScene: windowScene)
        window?.rootViewController = RideBridgeViewController()
        window?.overrideUserInterfaceStyle = .dark
        window?.makeKeyAndVisible()

        // スライドショーのBGMを消音スイッチ中でも鳴らす（他アプリの音楽は止めない）
        try? AVAudioSession.sharedInstance().setCategory(.playback, mode: .default, options: [.mixWithOthers])

        SceneDelegateProxy.shared.scene(scene, willConnectTo: session, options: connectionOptions)
    }

    func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) {
        SceneDelegateProxy.shared.scene(scene, openURLContexts: URLContexts)
    }

    func scene(_ scene: UIScene, continue userActivity: NSUserActivity) {
        SceneDelegateProxy.shared.scene(scene, continue: userActivity)
    }
}

/// アプリ専用プラグイン（RidePhotos）を登録するためのビューコントローラ
class RideBridgeViewController: CAPBridgeViewController {
    override open func capacitorDidLoad() {
        bridge?.registerPluginInstance(RidePhotosPlugin())
    }

    override var preferredStatusBarStyle: UIStatusBarStyle { .lightContent }
}

/// カメラロールから「走行中に撮った写真」を探して渡す／動画を写真アプリへ保存する
@objc(RidePhotosPlugin)
public class RidePhotosPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "RidePhotosPlugin"
    public let jsName = "RidePhotos"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "requestAccess", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "listPhotos", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "getPhoto", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "saveVideo", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "saveImage", returnType: CAPPluginReturnPromise)
    ]

    private static func statusString(_ s: PHAuthorizationStatus) -> String {
        switch s {
        case .authorized: return "authorized"
        case .limited: return "limited"
        case .denied, .restricted: return "denied"
        default: return "notDetermined"
        }
    }

    @objc func requestAccess(_ call: CAPPluginCall) {
        PHPhotoLibrary.requestAuthorization(for: .readWrite) { status in
            call.resolve(["status": RidePhotosPlugin.statusString(status)])
        }
    }

    /// from / to: ミリ秒（UNIX時間）。その間に撮影された写真（スクリーンショット除く）を返す
    @objc func listPhotos(_ call: CAPPluginCall) {
        let from = call.getDouble("from") ?? 0
        let to = call.getDouble("to") ?? Date().timeIntervalSince1970 * 1000
        let opts = PHFetchOptions()
        opts.predicate = NSPredicate(format: "creationDate >= %@ AND creationDate <= %@",
                                     Date(timeIntervalSince1970: from / 1000) as NSDate,
                                     Date(timeIntervalSince1970: to / 1000) as NSDate)
        opts.sortDescriptors = [NSSortDescriptor(key: "creationDate", ascending: true)]
        let result = PHAsset.fetchAssets(with: .image, options: opts)
        var list: [[String: Any]] = []
        result.enumerateObjects { asset, _, _ in
            if asset.mediaSubtypes.contains(.photoScreenshot) { return }
            var o: [String: Any] = [
                "id": asset.localIdentifier,
                "t": (asset.creationDate?.timeIntervalSince1970 ?? 0) * 1000,
                "w": asset.pixelWidth,
                "h": asset.pixelHeight
            ]
            if let loc = asset.location {
                o["lat"] = loc.coordinate.latitude
                o["lon"] = loc.coordinate.longitude
            }
            list.append(o)
        }
        call.resolve(["photos": list])
    }

    /// 長辺 maxSize に縮小した JPEG を base64 で返す（iCloud上の写真もダウンロード）
    @objc func getPhoto(_ call: CAPPluginCall) {
        guard let id = call.getString("id"),
              let asset = PHAsset.fetchAssets(withLocalIdentifiers: [id], options: nil).firstObject else {
            call.reject("photo not found"); return
        }
        let maxSize = CGFloat(call.getInt("maxSize") ?? 2048)
        let longSide = CGFloat(max(asset.pixelWidth, asset.pixelHeight, 1))
        let scale = min(1, maxSize / longSide)
        let size = CGSize(width: CGFloat(asset.pixelWidth) * scale, height: CGFloat(asset.pixelHeight) * scale)
        let o = PHImageRequestOptions()
        o.isNetworkAccessAllowed = true
        o.deliveryMode = .highQualityFormat
        o.resizeMode = .exact
        o.isSynchronous = false
        PHImageManager.default().requestImage(for: asset, targetSize: size, contentMode: .aspectFit, options: o) { image, _ in
            guard let image = image, let data = image.jpegData(compressionQuality: 0.85) else {
                call.reject("could not load photo"); return
            }
            call.resolve(["data": data.base64EncodedString()])
        }
    }

    /// path: Filesystem プラグインが書き出した file:// URI
    @objc func saveVideo(_ call: CAPPluginCall) {
        guard let path = call.getString("path"), let src = URL(string: path) else {
            call.reject("invalid path"); return
        }
        PHPhotoLibrary.requestAuthorization(for: .addOnly) { status in
            guard status == .authorized || status == .limited else { call.reject("denied"); return }
            // ブラウザ録画の MP4 は写真アプリが受け付けないことがあるため、通常の MP4 に書き直してから保存
            RidePhotosPlugin.remux(src) { fixed in
                let url = fixed ?? src
                PHPhotoLibrary.shared().performChanges({
                    PHAssetChangeRequest.creationRequestForAssetFromVideo(atFileURL: url)
                }) { ok, err in
                    if ok { call.resolve() } else { call.reject(err?.localizedDescription ?? "save failed") }
                }
            }
        }
    }

    /// path: Filesystem プラグインが書き出した file:// URI（JPEG）
    @objc func saveImage(_ call: CAPPluginCall) {
        guard let path = call.getString("path"), let url = URL(string: path) else {
            call.reject("invalid path"); return
        }
        PHPhotoLibrary.requestAuthorization(for: .addOnly) { status in
            guard status == .authorized || status == .limited else { call.reject("denied"); return }
            PHPhotoLibrary.shared().performChanges({
                PHAssetChangeRequest.creationRequestForAssetFromImage(atFileURL: url)
            }) { ok, err in
                if ok { call.resolve() } else { call.reject(err?.localizedDescription ?? "save failed") }
            }
        }
    }

    private static func remux(_ src: URL, completion: @escaping (URL?) -> Void) {
        let asset = AVURLAsset(url: src)
        guard let export = AVAssetExportSession(asset: asset, presetName: AVAssetExportPresetPassthrough) else {
            completion(nil); return
        }
        let out = FileManager.default.temporaryDirectory.appendingPathComponent("ridelog_\(Int(Date().timeIntervalSince1970)).mp4")
        try? FileManager.default.removeItem(at: out)
        export.outputURL = out
        export.outputFileType = .mp4
        export.exportAsynchronously {
            completion(export.status == .completed ? out : nil)
        }
    }
}
