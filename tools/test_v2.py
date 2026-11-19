import os as _os
ROOT=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
APP=_os.environ.get('APP_DIR', ROOT+'/www')
TESTDATA=_os.environ.get('TESTDATA', '/tmp/ridelog-testdata')
SHOTS=_os.environ.get('SHOTS', '/tmp/ridelog-shots')
_os.makedirs(TESTDATA, exist_ok=True); _os.makedirs(SHOTS, exist_ok=True)
import asyncio, subprocess, time, base64, io, re, os
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright
srv = subprocess.Popen(['python3','-m','http.server','8125','-d',APP],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
OUT=''+SHOTS+'/v2'; os.makedirs(OUT,exist_ok=True)
def png(im):
    b=io.BytesIO(); im.save(b,'PNG'); return b.getvalue()
def std_tile(z,x,y,pale=False):
    im=Image.new('RGB',(256,256),(238,236,230) if pale else (226,232,220)); d=ImageDraw.Draw(im)
    for k in range(0,256,64): d.line([(k,0),(k,256)],fill=(200,200,200)); d.line([(0,k),(256,k)],fill=(200,200,200))
    d.line([(0,(x*37)%256),(256,(y*53)%256)],fill=(250,250,250),width=6)
    d.text((8,8),f'{z}/{x}/{y}',fill=(120,120,120)); return png(im)
def dem_tile(z,x,y):
    im=Image.new('RGB',(256,256)); px=im.load()
    for i in range(256):
        gx=x*256+i; h=300+250*(1+__import__('math').sin(gx/90.0)); v=int(h*100)
        for j in range(256): px[i,j]=((v>>16)&255,(v>>8)&255,v&255)
    return png(im)
async def tiles(route):
    m=re.search(r'xyz/(\w+)/(\d+)/(\d+)/(\d+)',route.request.url); kind,z,x,y=m.group(1),*map(int,m.groups()[1:])
    body = dem_tile(z,x,y) if kind=='dem_png' else std_tile(z,x,y,kind=='pale')
    await route.fulfill(status=200, body=body, headers={'Content-Type':'image/png','Access-Control-Allow-Origin':'*'})
async def nomi(route):
    await route.fulfill(status=200, body='{"address":{"province":"長野県","city":"松本市"}}', headers={'Content-Type':'application/json','Access-Control-Allow-Origin':'*'})
async def main():
  async with async_playwright() as p:
    b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--autoplay-policy=no-user-gesture-required'])
    ctx = await b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2, timezone_id='Asia/Tokyo', locale='ja-JP', accept_downloads=True,
        geolocation={'latitude':35.70,'longitude':139.50,'accuracy':8}, permissions=['geolocation'])
    await ctx.route(re.compile(r'cyberjapandata\.gsi\.go\.jp'), tiles)
    await ctx.route(re.compile(r'nominatim'), nomi)
    pg = await ctx.new_page(); errs=[]
    pg.on('pageerror', lambda e: errs.append('PAGE '+str(e)))
    pg.on('console', lambda m: m.type=='error' and 'openstreetmap' not in m.text and errs.append(m.text))
    await pg.goto('http://localhost:8125/'); await pg.wait_for_timeout(600)
    # live + fuel
    await pg.click('#btnStart')
    for i in range(5):
      await ctx.set_geolocation({'latitude':35.70+i*0.0003,'longitude':139.50,'accuracy':8}); await pg.wait_for_timeout(1050)
    await pg.click('#btnFuelLive'); await pg.fill('#fL','11.2'); await pg.fill('#fY','1950'); await pg.click('#sheet [data-a="1"]'); await pg.wait_for_timeout(300)
    await pg.click('#btnStop'); await pg.wait_for_timeout(200); await pg.click('#sheet [data-a="1"]'); await pg.wait_for_timeout(1200)
    # synthetic trip (with fuel full entries for economy across trips)
    await pg.evaluate("""async()=>{
      const mk=async(id,day,name,fuel)=>{const start=new Date(2026,10,day,9,0,0).getTime(); const pts=[]; let lat=35.70, lon=139.50; let t=start; const end=start+4*3600e3;
      while(t<end){ const min=(t-start)/60000; let v; if(min>=90&&min<110) v=0; else v=12+10*Math.sin(min/9);
        if(v>0){ lon -= v*2/(111320*Math.cos(lat*Math.PI/180))*0.8; lat += v*2/111320*0.6*Math.sin(min/20); }
        pts.push({t,lat:+lat.toFixed(6),lon:+lon.toFixed(6),acc:8,spd:+v.toFixed(2)}); t+=2000; }
      const tr={id,start,end,status:'done',name,points:pts,fuel}; tr.stats=computeStats(pts,start,end); await idbPut('trips',tr); return tr.stats.dist; };
      const d1=await mk('t1',8,'前回のツーリング',[{id:'fa',t:0,liters:10,yen:1800,full:true,dist:250000}]);
      await mk('tsyn',15,'奥多摩〜山梨 ツーリング',[{id:'fb',t:0,liters:9.5,yen:1700,full:true,dist:150000}]);
    }""")
    await pg.evaluate("openTrip('tsyn')"); await pg.wait_for_timeout(2500)
    await pg.fill('#detMemo','紅葉がきれいだった。ほうとうが美味しかった！帰りは中央道が少し渋滞。'); await pg.wait_for_timeout(900)
    print('memo saved:', await pg.evaluate("(async()=>(await idbGet('trips','tsyn')).memo)()"))
    print('fuel:', await pg.text_content('#fuelSum'), '|', (await pg.text_content('#fuelList'))[:80])
    print('elev:', await pg.text_content('#eleNote'))
    await pg.set_input_files('#addPhotos', [f'{TESTDATA}/photo{i}.jpg' for i in range(1,5)]); await pg.wait_for_timeout(3500)
    # chart cursor
    await pg.locator('#spdChart').scroll_into_view_if_needed(); await pg.wait_for_timeout(200)
    box = await pg.locator('#spdChart').bounding_box()
    await pg.mouse.click(box['x']+box['width']*0.55, box['y']+60); await pg.wait_for_timeout(300)
    print('tip:', await pg.text_content('#chartTip'))
    await pg.locator('#spdChart').scroll_into_view_if_needed(); await pg.wait_for_timeout(200)
    await pg.locator('.chartcard').screenshot(path=f'{OUT}/charts.png')
    # replay
    await pg.locator('#detMap').scroll_into_view_if_needed()
    await pg.select_option('#rpSpeed','300'); await pg.click('#rpPlay'); await pg.wait_for_timeout(2500)
    print('replay:', await pg.text_content('#rpInfo'), 'seek', await pg.input_value('#rpSeek'))
    await pg.screenshot(path=f'{OUT}/replay.png')
    await pg.click('#rpPlay')
    await pg.screenshot(path=f'{OUT}/detail_full.png', full_page=True)
    # summary image
    await pg.click('#btnShare'); await pg.wait_for_selector('#sheet img', timeout=30000)
    src = await pg.get_attribute('#sheet img','src')
    data = await pg.evaluate(f"fetch('{src}').then(r=>r.blob()).then(b=>new Promise(res=>{{const f=new FileReader();f.onload=()=>res(f.result);f.readAsDataURL(b)}}))")
    open(f'{OUT}/summary.jpg','wb').write(base64.b64decode(data.split(',')[1]))
    await pg.click('#sheet [data-a=close]')
    # slideshow: 1s, BGM random
    await pg.select_option('#ssDur','1')
    await pg.click('#btnPlay'); await pg.wait_for_function("document.querySelector('#player').classList.contains('on')", timeout=90000)
    print('bgm:', await pg.text_content('#bgmName'), 'total', await pg.evaluate('P.total'), 'bigOk', await pg.evaluate('P.big.ok'), 'miniOk', await pg.evaluate('P.mini.ok'))
    for name,tt in [('title_mid',2.0),('title_end',4.2),('photo2',6.0),('end',9.5)]:
      await pg.evaluate(f"(async()=>{{pause(); P.t={tt}; for(let k=0;k<40&&!ensureLoaded(P.t);k++) await new Promise(r=>setTimeout(r,50)); renderAt(P.t);}})()"); await pg.wait_for_timeout(200)
      d = await pg.evaluate("document.querySelector('#stage').toDataURL('image/jpeg',.85)"); open(f'{OUT}/ss_{name}.jpg','wb').write(base64.b64decode(d.split(',')[1]))
    await pg.click('#pShuffle'); await pg.wait_for_function("!document.querySelector('#bgmName').textContent.includes('準備中')", timeout=60000); print('bgm2:', await pg.text_content('#bgmName'))


    await pg.click('#pRec')
    for i in range(25):
      await pg.wait_for_timeout(1000)
      st=await pg.evaluate("JSON.stringify({t:P.t.toFixed(2),total:P.total,playing:P.playing,stalled:P.stalled,rec:P.rec&&P.rec.state,ac:AU.ctx&&AU.ctx.state,idx:slideIndex(P.t),need:needed(P.t),cache:[...P.cache.keys()],loading:[...P.loading],video:!!document.querySelector('#sheet video')})")
      print(st)
      if '"video":true' in st: break
    print('video:', await pg.text_content('#sheet .muted'))
    await pg.click('#sheet [data-a=close]'); await pg.click('#pClose')
    # backup & restore
    await pg.click('#btnBack'); await pg.wait_for_timeout(500)
    async with pg.expect_download() as dl: await pg.click('#btnBackup')
    d = await dl.value; path=f'{OUT}/backup.ridelog'; await d.save_as(path); print('backup bytes', os.path.getsize(path))
    await pg.evaluate("(async()=>{for(const t of await idbAll('trips')) await idbDel('trips',t.id); for(const p of await idbAll('photos')) await idbDel('photos',p.id);})()")
    await pg.set_input_files('#restoreFile', path); await pg.wait_for_timeout(500); await pg.click('#sheet [data-a="1"]'); await pg.wait_for_timeout(2500)
    print('restored', await pg.evaluate("(async()=>[(await idbAll('trips')).length,(await idbAll('photos')).length])()"))
    await pg.screenshot(path=f'{OUT}/home.png', full_page=True)
    print('errors', errs[:8])
    await b.close()
try: asyncio.run(main())
finally: srv.terminate()
