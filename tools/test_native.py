import os as _os
ROOT=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
APP=_os.environ.get('APP_DIR', ROOT+'/www')
TESTDATA=_os.environ.get('TESTDATA', '/tmp/ridelog-testdata')
SHOTS=_os.environ.get('SHOTS', '/tmp/ridelog-shots')
_os.makedirs(TESTDATA, exist_ok=True); _os.makedirs(SHOTS, exist_ok=True)
import asyncio, subprocess, time, base64
from playwright.async_api import async_playwright
srv = subprocess.Popen(['python3','-m','http.server','8124','-d',APP],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
img = base64.b64encode(open(''+TESTDATA+'/photo3.jpg','rb').read()).decode()
MOCK = """
window.__calls=[];
window.webkit={messageHandlers:{bridge:{postMessage(){}}}};
const H=(n,ms)=>({name:n,methods:ms.map(([m,r])=>({name:m,rtype:r||'promise'}))});
window.Capacitor={
  PluginHeaders:[H('BackgroundGeolocation',[['addWatcher','callback'],['removeWatcher'],['openSettings']]),
    H('Filesystem',[['writeFile']]),H('Share',[['share']]),H('RidePhotos',[['requestAccess'],['listPhotos'],['getPhoto'],['saveVideo']])],
  nativeCallback(p,m,o,cb){ __calls.push(p+'.'+m); window.__cb=(loc)=>cb(loc); return 'cb1'; },
  nativePromise(p,m,o){ __calls.push(p+'.'+m);
    if(p==='RidePhotos'&&m==='requestAccess') return Promise.resolve({status:'authorized'});
    if(p==='RidePhotos'&&m==='listPhotos') return Promise.resolve({photos:[{id:'A1',t:Date.now()-3000,w:2000,h:1125},{id:'A2',t:Date.now()-2000,w:2000,h:1125,lat:35.9,lon:138.4}]});
    if(p==='RidePhotos'&&m==='getPhoto') return Promise.resolve({data:'IMG'});
    if(p==='Filesystem') return Promise.resolve({uri:'file:///tmp/x'});
    return Promise.resolve({});
  }
};
""".replace('IMG', img)
async def main():
  async with async_playwright() as p:
    b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
    ctx = await b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2, timezone_id='Asia/Tokyo')
    await ctx.add_init_script(MOCK)
    pg = await ctx.new_page(); errs=[]
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto('http://localhost:8124/'); await pg.wait_for_timeout(500)
    await pg.screenshot(path=''+SHOTS+'/n1_home.png')
    await pg.click('#btnStart'); await pg.wait_for_timeout(300)
    for i in range(6):
      await pg.evaluate(f"__cb({{latitude:35.7+{i}*0.0003,longitude:139.5,accuracy:6,speed:12,time:Date.now()}})"); await pg.wait_for_timeout(1000)
    await pg.screenshot(path=''+SHOTS+'/n2_live.png')
    await pg.click('#btnStop'); await pg.wait_for_timeout(200); await pg.click('#sheet [data-a="1"]')
    await pg.wait_for_timeout(3000)
    print('photos', await pg.evaluate("S.photos.map(p=>[p.assetId,p.src,p.lat])"))
    await pg.screenshot(path=''+SHOTS+'/n3_detail.png', full_page=True)
    # 壊れた写真（中身が空）を作って、カメラロールから修復されるか
    await pg.evaluate("(async()=>{const ps=await photosOf(S.detail.id); const p=ps.find(x=>x.assetId==='A1'); p.thumb=new Blob([]); p.blob=new Blob([]); await idbPut('photos',p); await renderPhotos();})()")
    await pg.wait_for_timeout(1500)
    print('repaired', await pg.evaluate("S.photos.map(p=>[p.assetId,p.broken,p.thumb.size>0])"), await pg.text_content('#toast'))
    print('calls', await pg.evaluate("[...new Set(__calls)]"))
    print('native?', await pg.evaluate('NATIVE')); print('errors', errs)
    await b.close()
try: asyncio.run(main())
finally: srv.terminate()
