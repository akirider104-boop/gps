import os as _os
ROOT=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
APP=_os.environ.get('APP_DIR', ROOT+'/www')
TESTDATA=_os.environ.get('TESTDATA', '/tmp/ridelog-testdata')
SHOTS=_os.environ.get('SHOTS', '/tmp/ridelog-shots')
_os.makedirs(TESTDATA, exist_ok=True); _os.makedirs(SHOTS, exist_ok=True)
from PIL import Image, ImageDraw
import datetime as dt
out=''+TESTDATA+''
base=dt.datetime(2026,11,15,9,0,0)
specs=[(30,None,(1600,1200),'#3a7'),(75,(35.95,138.45),(1200,1600),'#a73'),(130,None,(2000,1125),'#37a'),(200,None,(1600,1200),'#a37'),(600,None,(1600,1200),'#777')]
for i,(mins,gps,size,col) in enumerate(specs):
    im=Image.new('RGB',size,col); d=ImageDraw.Draw(im)
    for k in range(0,size[0],80): d.line([(k,0),(k,size[1])],fill='#ffffff',width=3)
    d.ellipse([size[0]//2-200,size[1]//2-200,size[0]//2+200,size[1]//2+200],fill='#fff')
    ex=im.getexif()
    t=(base+dt.timedelta(minutes=mins)).strftime('%Y:%m:%d %H:%M:%S')
    ex[0x0132]=t
    ifd=ex.get_ifd(0x8769); ifd[0x9003]=t
    if gps:
        g=ex.get_ifd(0x8825)
        def dms(v): 
            d_=int(v); m=int((v-d_)*60); s=round(((v-d_)*60-m)*60*100)
            from fractions import Fraction as F; return (F(d_),F(m),F(s,100))
        g[1]='N'; g[2]=dms(gps[0]); g[3]='E'; g[4]=dms(gps[1])
    im.save(f'{out}/photo{i+1}.jpg',exif=ex,quality=85)
print('ok')
