import os as _os
ROOT=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
APP=_os.environ.get('APP_DIR', ROOT+'/www')
SHOTS=_os.environ.get('SHOTS', '/tmp/ridelog-shots'); _os.makedirs(SHOTS, exist_ok=True)
# 不安定な地図サーバーでも黒い欠けが出ないか（再試行・広域タイルでの穴埋め）
import asyncio, subprocess, time, re, io, random, base64
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright
srv = subprocess.Popen(['python3','-m','http.server','8130','-d',APP],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
seen = {}
def png(z,x,y):
    im=Image.new('RGB',(256,256),(226,232,220)); d=ImageDraw.Draw(im); d.rectangle([0,0,255,255],outline=(190,190,190)); d.text((8,8),f'{z}/{x}/{y}',fill=(90,90,90))
    b=io.BytesIO(); im.save(b,'PNG'); return b.getvalue()
async def tiles(route):
    m=re.search(r'xyz/(\w+)/(\d+)/(\d+)/(\d+)',route.request.url); z,x,y=map(int,m.groups()[1:])
    key=(z,x,y); seen[key]=seen.get(key,0)+1
    if (x*7+y*3) % 9 == 0 and z >= 12: return await route.abort()          # 一部は何度やっても取れない → 広域で穴埋め
    if seen[key] == 1 and random.random() < .5: return await route.abort()  # 半分は初回失敗 → 再試行
    await route.fulfill(status=200, body=png(z,x,y), headers={'Content-Type':'image/png','Access-Control-Allow-Origin':'*'})
async def main():
  async with async_playwright() as p:
    b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
    ctx = await b.new_context(viewport={'width':390,'height':844}); await ctx.route(re.compile(r'cyberjapandata'), tiles)
    pg = await ctx.new_page(); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto('http://localhost:8130/'); await pg.wait_for_timeout(500)
    r = await pg.evaluate("""async()=>{const pts=[]; let t=Date.now(); for(let i=0;i<300;i++) pts.push({t:t+i*2000,lat:35.85+i*0.0003,lon:140.55+i*0.0004,acc:8});
      const t0=performance.now(); const m=await baseMap(pts,1920,1080,{fill:.62}); const ms=performance.now()-t0;
      const d=m.canvas.getContext('2d').getImageData(0,0,1920,1080).data; let dark=0; for(let i=0;i<d.length;i+=4){ if(d[i]<60&&d[i+1]<60&&d[i+2]<70) dark++; }
      window.__c=m.canvas; return {ok:m.ok, complete:m.complete, z:m.z, darkPct:(dark/(1920*1080)*100).toFixed(2), sec:(ms/1000).toFixed(1)};}""")
    print('map', r)
    d = await pg.evaluate("__c.toDataURL('image/jpeg',.7)"); open(f'{SHOTS}/tiles_flaky.jpg','wb').write(base64.b64decode(d.split(',')[1]))
    print('errors', errs); await b.close()
try: asyncio.run(main())
finally: srv.terminate()
