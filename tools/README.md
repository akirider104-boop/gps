# テスト用ツール（Claude作業用）

- `mkphotos.py` … EXIF付きテスト写真を作る（最初に1回）
- `test_v2.py` … 全機能のブラウザテスト（地図・標高タイルと地名検索はモック）
- `test_native.py` … iPhoneのネイティブブリッジを模擬したテスト
- `test_pause.py` … 一時停止のテスト
- `test_tiles.py` … 不安定な地図サーバーでも黒い欠けが出ないか
- `test_order.py` … 長押しドラッグでの全体並べ替え
- `test_media.py` … 動画・他機器の写真（素材: ffmpeg で `vid_in.mp4`(creation_time付き) / `vid_none.mp4`、PILで `other_noexif.jpg` を TESTDATA に作る）
- `render_ios_assets.py` … assets/icon.svg からアプリアイコン・起動画面を生成

前提: Python + playwright、/usr/bin/google-chrome。`www/` を `-d` で配信してテストします。
