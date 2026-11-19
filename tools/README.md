# テスト用ツール（Claude作業用）

- `mkphotos.py` … EXIF付きテスト写真を作る（最初に1回）
- `test_v2.py` … 全機能のブラウザテスト（地図・標高タイルと地名検索はモック）
- `test_native.py` … iPhoneのネイティブブリッジを模擬したテスト
- `test_pause.py` … 一時停止のテスト
- `render_ios_assets.py` … assets/icon.svg からアプリアイコン・起動画面を生成

前提: Python + playwright、/usr/bin/google-chrome。`www/` を `-d` で配信してテストします。
