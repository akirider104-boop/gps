import os as _os
ROOT=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
APP=_os.environ.get('APP_DIR', ROOT+'/www')
TESTDATA=_os.environ.get('TESTDATA', '/tmp/ridelog-testdata')
SHOTS=_os.environ.get('SHOTS', '/tmp/ridelog-shots')
_os.makedirs(TESTDATA, exist_ok=True); _os.makedirs(SHOTS, exist_ok=True)
import asyncio
from playwright.async_api import async_playwright
from PIL import Image
svg = open(''+ROOT+'/assets/icon.svg').read().replace('<svg ', '<svg width="100%" height="100%" ', 1)
A=''+ROOT+'/ios/App/App/Assets.xcassets'
async def main():
  async with async_playwright() as p:
    b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
    pg = await b.new_page(viewport={'width':1024,'height':1024})
    await pg.set_content(f'<body style="margin:0">{svg}</body>'); await pg.screenshot(path='/tmp/icon1024.png')
    await b.close()
asyncio.run(main())
Image.open('/tmp/icon1024.png').convert('RGB').save(f'{A}/AppIcon.appiconset/AppIcon-512@2x.png')
ic = Image.open('/tmp/icon1024.png').convert('RGB').resize((560,560), Image.LANCZOS)
sp = Image.new('RGB',(2732,2732),(11,15,21)); sp.paste(ic,((2732-560)//2,(2732-560)//2))
for n in ['splash-2732x2732.png','splash-2732x2732-1.png','splash-2732x2732-2.png']: sp.save(f'{A}/Splash.imageset/{n}')
print('ok')
