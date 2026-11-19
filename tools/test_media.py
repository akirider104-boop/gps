import os as _os
ROOT=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
APP=_os.environ.get('APP_DIR', ROOT+'/www')
TESTDATA=_os.environ.get('TESTDATA', '/tmp/ridelog-testdata')
SHOTS=_os.environ.get('SHOTS', '/tmp/ridelog-shots')
_os.makedirs(SHOTS, exist_ok=True)
# 動画・他機器の写真・日時なし分の並べ替えのテスト（先に mkphotos.py と ffmpeg でテスト素材を作る）
import asyncio, subprocess, time, base64, re
from playwright.async_api import async_playwright
srv = subprocess.Popen(['python3','-m','http.server','8128','-d',APP],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
async def block(route): await route.fulfill(status=404, body='')
async def main():
  async with async_playwright() as p:
    b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--autoplay-policy=no-user-gesture-required'])
    ctx = await b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2, timezone_id='Asia/Tokyo')
    await ctx.route(re.compile(r'cyberjapandata|nominatim|openstreetmap'), block)
    pg = await ctx.new_page(); errs=[]
    pg.on('pageerror', lambda e: errs.append('PAGE '+str(e)))
    pg.on('console', lambda m: m.type=='error' and 'Failed to load resource' not in m.text and errs.append(m.text))
    await pg.goto('http://localhost:8128/'); await pg.wait_for_timeout(500)
    await pg.evaluate("""async()=>{const start=new Date(2026,10,15,9,0,0).getTime(); const pts=[]; let lat=35.7,lon=139.5,t=start; const end=start+4*3600e3;
      while(t<end){const v=15; lon-=v*2/(111320*Math.cos(lat*Math.PI/180))*0.8; lat+=v*2/111320*0.3; pts.push({t,lat:+lat.toFixed(6),lon:+lon.toFixed(6),acc:8,spd:v}); t+=2000;}
      const tr={id:'tm',start,end,status:'done',name:'メディアテスト',points:pts}; tr.stats=computeStats(pts,start,end); await idbPut('trips',tr);}""")
    await pg.evaluate("openTrip('tm')"); await pg.wait_for_timeout(1200)
    files=[f'{TESTDATA}/{n}' for n in ['vid_none.mp4','photo5.jpg','photo1.jpg','other_noexif.jpg','vid_in.mp4','photo3.jpg']]
    await pg.set_input_files('#addPhotos', files); await pg.wait_for_function("!document.querySelector('#toast').textContent.includes('読み込み中')", timeout=60000)
    print('toast:', await pg.text_content('#toast'))
    order = await pg.evaluate("S.photos.map(p=>[p.kind, p.t?new Date(p.t).toLocaleTimeString('ja-JP'):null, inTrip(p), p.dur?+p.dur.toFixed(1):null])")
    print('order:', order)
    await pg.locator('#photoGrid').scroll_into_view_if_needed(); await pg.locator('#photoGrid').screenshot(path=f'{SHOTS}/media_grid.png')
    # slideshow
    await pg.select_option('#ssDur','2'); await pg.select_option('#ssBgm','off')
    await pg.click('#btnPlay'); await pg.wait_for_function("document.querySelector('#player').classList.contains('on')", timeout=60000)
    sl = await pg.evaluate("P.slides.map(s=>s.type==='photo'?(s.video?'V':'P')+(s.rin?'+':'-')+s.dur.toFixed(1):s.type)")
    print('slides:', sl, 'total', await pg.evaluate('P.total'))
    # render a frame mid video-in-trip slide and an extra slide
    for name, cond in [('vid_in', "s.video&&s.rin"), ('extra_photo', "!s.video&&!s.rin"), ('extra_vid', "s.video&&!s.rin")]:
      t = await pg.evaluate(f"(()=>{{const s=P.slides.find(s=>s.type==='photo'&&({cond})); return s? s.t0+s.dur*0.5 : null}})()")
      if t is None: print('no slide', name); continue
      await pg.evaluate(f"""(async()=>{{pause(); P.t={t}; for(let k=0;k<80&&!ensureLoaded(P.t);k++) await new Promise(r=>setTimeout(r,50));
        syncVideos(P.t,true); await new Promise(r=>setTimeout(r,500)); syncVideos(P.t,false); renderAt(P.t);}})()""")
      d = await pg.evaluate("document.querySelector('#stage').toDataURL('image/jpeg',.8)"); open(f'{SHOTS}/media_{name}.jpg','wb').write(base64.b64decode(d.split(',')[1]))
    await pg.click('#pRec')
    for i in range(60):
      await pg.wait_for_timeout(1000)
      if await pg.evaluate("!!document.querySelector('#sheet video')"): break
    print('video:', await pg.text_content('#sheet .muted') if await pg.evaluate("!!document.querySelector('#sheet video')") else 'NOT FINISHED t='+str(await pg.evaluate('P.t')))
    print('errors', errs[:6]); await b.close()
try: asyncio.run(main())
finally: srv.terminate()
