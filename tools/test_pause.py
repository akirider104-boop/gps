import os as _os
ROOT=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
APP=_os.environ.get('APP_DIR', ROOT+'/www')
TESTDATA=_os.environ.get('TESTDATA', '/tmp/ridelog-testdata')
SHOTS=_os.environ.get('SHOTS', '/tmp/ridelog-shots')
_os.makedirs(TESTDATA, exist_ok=True); _os.makedirs(SHOTS, exist_ok=True)
import asyncio, subprocess, time
from playwright.async_api import async_playwright
srv = subprocess.Popen(['python3','-m','http.server','8127','-d',APP],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
async def main():
  async with async_playwright() as p:
    b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
    ctx = await b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2, timezone_id='Asia/Tokyo', geolocation={'latitude':35.70,'longitude':139.50,'accuracy':8}, permissions=['geolocation'])
    pg = await ctx.new_page(); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto('http://localhost:8127/'); await pg.wait_for_timeout(500)
    # unit: synthetic trip with a 20-min pause and a 300 m jump across it
    r = await pg.evaluate("""()=>{const s=Date.now()-3600e3; const pts=[]; let lat=35.7;
      for(let i=0;i<600;i++){ pts.push({t:s+i*2000,lat:+(lat+=0.0002).toFixed(6),lon:139.5,acc:8,spd:20}); }      // 20 min driving
      const ps=s+1200e3, pe=ps+1200e3; lat+=0.003;                                                               // 300m jump while paused
      for(let i=0;i<600;i++){ pts.push({t:pe+i*2000,lat:+(lat+=0.0002).toFixed(6),lon:139.5,acc:8,spd:20}); }
      const a=computeStats(pts,s,pe+1200e3,[{from:ps,to:pe}]), b=computeStats(pts,s,pe+1200e3);
      return {withPause:{km:(a.dist/1000).toFixed(2),rest:a.rest,spans:a.restSpans.length,paused:a.restSpans.filter(x=>x.paused).length}, noPause:{km:(b.dist/1000).toFixed(2),rest:b.rest}};}""")
    print('unit', r)
    # live flow
    await pg.click('#btnStart')
    for i in range(4):
      await ctx.set_geolocation({'latitude':35.70+i*0.0003,'longitude':139.50,'accuracy':8}); await pg.wait_for_timeout(1050)
    await pg.click('#btnPause'); await pg.wait_for_timeout(300)
    await ctx.set_geolocation({'latitude':35.703,'longitude':139.503,'accuracy':8})   # walked away while paused
    await pg.wait_for_timeout(2500)
    await pg.screenshot(path=''+SHOTS+'/pause_live.png')
    st = await pg.evaluate("({n:S.trip.points.length, paused:isPaused(), btn:document.querySelector('#btnPause').textContent, clock:document.querySelector('#liveClock').textContent, spd:document.querySelector('#lvSpeed').textContent, watch:S.watchId})")
    print('paused state', st)
    # reload while paused -> stays paused
    await pg.reload(); await pg.wait_for_timeout(1200)
    print('after reload', await pg.evaluate("({paused:isPaused(), watch:S.watchId, view:document.querySelector('#live').classList.contains('on')})"))
    await pg.click('#btnPause'); await pg.wait_for_timeout(300)
    for i in range(4):
      await ctx.set_geolocation({'latitude':35.703+i*0.0003,'longitude':139.503,'accuracy':8}); await pg.wait_for_timeout(1050)
    print('resumed', await pg.evaluate("({n:S.trip.points.length, paused:isPaused(), dist:document.querySelector('#lvDist').textContent, rest:document.querySelector('#lvRest').textContent})"))
    await pg.click('#btnStop'); await pg.wait_for_timeout(200); await pg.click('#sheet [data-a="1"]'); await pg.wait_for_timeout(1200)
    print('detail', await pg.evaluate("({dist:S.detail.stats.dist.toFixed(0), rest:S.detail.stats.rest.toFixed(0), pauses:S.detail.pauses})"))
    print('errors', errs); await b.close()
try: asyncio.run(main())
finally: srv.terminate()
