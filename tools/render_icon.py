import os as _os
ROOT=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
APP=_os.environ.get('APP_DIR', ROOT+'/www')
TESTDATA=_os.environ.get('TESTDATA', '/tmp/ridelog-testdata')
SHOTS=_os.environ.get('SHOTS', '/tmp/ridelog-shots')
_os.makedirs(TESTDATA, exist_ok=True); _os.makedirs(SHOTS, exist_ok=True)
import sys, asyncio
from playwright.async_api import async_playwright
src, out_dir = sys.argv[1], sys.argv[2]
svg = open(src).read()
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome")
        for name, size, pad in [("icon-512.png",512,0),("icon-192.png",192,0),("apple-touch-icon.png",180,0),("icon-maskable-512.png",512,0.1)]:
            pg = await b.new_page(viewport={"width":size,"height":size})
            inner = int(size*(1-2*pad))
            svg2 = svg.replace("<svg ", '<svg width="100%" height="100%" ', 1)
            html = f'<html><body style="margin:0;background:#0b0f15;display:flex;align-items:center;justify-content:center;width:{size}px;height:{size}px"><div style="width:{inner}px;height:{inner}px">{svg2}</div></body></html>'
            await pg.set_content(html)
            await pg.screenshot(path=f"{out_dir}/{name}")
        await b.close()
asyncio.run(main())
