# RideLog iPhoneアプリ版

Web版との違い
- **バックグラウンド記録**：記録中にGoogleマップなどのナビアプリや音楽アプリに切り替えても、画面をロックしても記録が続きます（画面上部に位置情報使用中の青い表示が出ます）
- **写真の自動取り込み**：■終了を押すと、走行中にiPhoneのカメラで撮った写真をカメラロールから自動で集めます。スライドショーは「写真に保存」から写真アプリへ直接保存できます

必要なもの：iPhone、Apple ID（無料で可）、Mac か Windows のPC、ケーブル

---

## A. Macがある場合（おすすめ）

1. App Storeから **Xcode 26以降** をインストール。あわせて Node.js（https://nodejs.org のLTS版）もインストール
2. このフォルダでターミナルを開いて次を実行
   ```
   npm install
   npx cap sync ios
   open ios/App/App.xcodeproj
   ```
3. Xcodeで左の「App」→ TARGETS「App」→「Signing & Capabilities」
   - Team：自分のApple IDを追加して選ぶ（Xcode → Settings → Accounts）
   - Bundle Identifier：`jp.ridelog.app` を、ほかの人と重ならない名前に変える（例 `jp.yamada.ridelog`）
4. iPhoneをケーブルでつなぎ、上部の実行先で自分のiPhoneを選んで ▶ を押す
5. iPhone側で
   - 初回は「設定 → プライバシーとセキュリティ → デベロッパモード」をオンにして再起動
   - 「設定 → 一般 → VPNとデバイス管理」で自分のApple IDを「信頼」

## B. Windowsしかない場合（GitHubのクラウドMacで作る）

1. GitHubで新しいリポジトリを作り、このフォルダの中身をアップロード（`node_modules` は除く）
2. リポジトリの「Actions」タブ →「Build iOS (unsigned ipa)」→「Run workflow」
3. 10〜20分で完了したら、実行結果の Artifacts から `RideLog-ipa` をダウンロードして解凍
4. PCに **Sideloadly**（https://sideloadly.io ）と、Apple公式の iTunes・iCloud（Microsoft Store版ではなくWeb版）をインストール
5. iPhoneをつないでSideloadlyを開き、`RideLog-unsigned.ipa` をドラッグ → Apple IDを入力 →「Start」
6. iPhone側の設定はAの手順5と同じ

---

## はじめて起動したとき
- 位置情報は **「Appの使用中は許可」** を選択。STARTを押してから別のアプリに切り替えても記録は続きます
- 写真は「フルアクセスを許可」を選ぶと自動取り込みが確実です（「写真を選択」にした場合は選んだ写真だけが対象）

## 注意
- **無料のApple IDでインストールしたアプリは7日で起動しなくなります**。同じ手順で入れ直せば、記録はそのまま残ります。入れ直しが面倒なら Apple Developer Program（年額99ドル、日本では1万数千円）に登録すると、1年間有効になります
- バッテリー消費はGPSの分だけ増えます。長距離ではUSB電源の併用がおすすめです
- 地図：国土地理院タイル／OpenStreetMap。地名：OpenStreetMap Nominatim（通信が必要）

## 中身を変更したとき
`www/` の中を編集したら `npx cap sync ios` を実行してからビルドし直してください。
