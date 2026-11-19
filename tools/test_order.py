import os as _os
ROOT=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
APP=_os.environ.get('APP_DIR', ROOT+'/www')
TESTDATA=_os.environ.get('TESTDATA', '/tmp/ridelog-testdata')
SHOTS=_os.environ.get('SHOTS', '/tmp/ridelog-shots')
_os.makedirs(SHOTS, exist_ok=True)
# 長押しドラッグでの全体並べ替えのテスト
import asyncio, subprocess, time, re
from playwright.async_api import async_playwright
srv = subprocess.Popen(['python3','-m','http.server','8129','-d',APP],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
async def block(route): await route.fulfill(status=404, body='')
async def drag(pg, src, dst):
  a = await src.bounding_box(); b = await dst.bounding_box()
  await pg.mouse.move(a['x']+a['width']/2, a['y']+a['height']/2); await pg.mouse.down(); await pg.wait_for_timeout(100)
  for k in range(1, 16):
    await pg.mouse.move(a['x']+a['width']/2 + (b['x']-a['x']-a['width']*0.25)*k/15, a['y']+a['height']/2 + (b['y']-a['y'])*k/15); await pg.wait_for_timeout(30)
  await pg.mouse.up(); await pg.wait_for_timeout(600)
async def main():
  async with async_playwright() as p:
    b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
    ctx = await b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2, timezone_id='Asia/Tokyo')
    await ctx.route(re.compile(r'cyberjapandata|nominatim|openstreetmap'), block)
    pg = await ctx.new_page(); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto('http://localhost:8129/'); await pg.wait_for_timeout(500)
    await pg.evaluate("""async()=>{const start=new Date(2026,10,15,9,0,0).getTime(); const pts=[]; let lat=35.7,lon=139.5,t=start; const end=start+4*3600e3;
      while(t<end){lon-=0.0002; pts.push({t,lat,lon:+lon.toFixed(6),acc:8,spd:15}); t+=2000;}
      const tr={id:'to',start,end,status:'done',name:'並べ替えテスト',points:pts}; tr.stats=computeStats(pts,start,end); await idbPut('trips',tr);}""")
    await pg.evaluate("openTrip('to')"); await pg.wait_for_timeout(1000)
    await pg.set_input_files('#addPhotos', [f'{TESTDATA}/{n}' for n in ['photo1.jpg','photo2.jpg','photo3.jpg','other_noexif.jpg']])
    await pg.wait_for_function("!document.querySelector('#toast').textContent.includes('読み込み中')", timeout=60000)
    lab = "S.photos.map(p=>(p.kind==='video'?'V':'P')+(p.t?new Date(p.t).getHours()+':'+String(new Date(p.t).getMinutes()).padStart(2,'0'):'--'))"
    print('initial', await pg.evaluate(lab))
    await pg.locator('#photoGrid').scroll_into_view_if_needed()
    tiles = pg.locator('#photoGrid .ph')
    await drag(pg, tiles.nth(3), tiles.nth(0))   # 日時なしを先頭へ
    print('after drag', await pg.evaluate(lab), 'custom', await pg.evaluate('S.detail.customOrder'))
    await drag(pg, tiles.nth(1), tiles.nth(3))   # 自動分(9:30)を後ろへ
    print('after drag2', await pg.evaluate(lab))
    await pg.reload(); await pg.wait_for_timeout(500); await pg.evaluate("openTrip('to')"); await pg.wait_for_timeout(1000)
    print('persisted', await pg.evaluate(lab))
    await pg.set_input_files('#addPhotos', [f'{TESTDATA}/photo4.jpg'])   # 12:20 を後から追加
    await pg.wait_for_function("!document.querySelector('#toast').textContent.includes('読み込み中')", timeout=60000)
    print('added later', await pg.evaluate(lab))
    await pg.select_option('#ssBgm','off'); await pg.click('#btnPlay'); await pg.wait_for_function("document.querySelector('#player').classList.contains('on')", timeout=60000)
    print('slides', await pg.evaluate("P.slides.filter(s=>s.p).map(s=>(s.rin?'+':'-')+(s.p.t?new Date(s.p.t).getHours()+':'+String(new Date(s.p.t).getMinutes()).padStart(2,'0'):'--'))"))
    await pg.click('#pClose')
    await pg.locator('#photoGrid').screenshot(path=f'{SHOTS}/order_grid.png')
    await pg.click('#btnOrderReset'); await pg.click('#sheet [data-a="1"]'); await pg.wait_for_timeout(800)
    print('reset', await pg.evaluate(lab), 'custom', await pg.evaluate('S.detail.customOrder'))
    print('errors', errs); await b.close()
try: asyncio.run(main())
finally: srv.terminate()
