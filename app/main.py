import csv,hmac,io,os,uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import qrcode
from fastapi import FastAPI,File,Form,HTTPException,Request,UploadFile
from fastapi.responses import FileResponse,HTMLResponse,RedirectResponse,StreamingResponse,Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from starlette.middleware.sessions import SessionMiddleware
from .database import con,init_db,settings,LEVEL,CRACK
from .model import POINTS,campaigns,grouped,crack_points,crack_point,assessment,regression,year_filter
from .reports import report
BASE=Path(__file__).parent
@asynccontextmanager
async def life(app):init_db();yield
app=FastAPI(title='Hausmonitor V5',version='5.0.0',lifespan=life);app.add_middleware(SessionMiddleware,secret_key=os.getenv('SECRET_KEY','change-me'));app.mount('/static',StaticFiles(directory=BASE/'static'),name='static');tpl=Jinja2Templates(directory=BASE/'templates')
def guard(r):
 if os.getenv('APP_PASSWORD','') and not r.session.get('ok'):return RedirectResponse('/login',303)
def photo(raw,typ,prefix,folder):
 if typ not in {'image/jpeg','image/png','image/webp'}:raise HTTPException(400,'Nur JPG, PNG oder WebP')
 Image.open(io.BytesIO(raw)).verify();ext={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'}[typ];n=f'{prefix}-{uuid.uuid4().hex}{ext}';(folder/n).write_bytes(raw);return n
@app.get('/health')
def health():return {'status':'ok','version':'5.0.0'}
@app.get('/login',response_class=HTMLResponse)
def lg(request:Request):return tpl.TemplateResponse(request=request,name='login.html',context={'error':None})
@app.post('/login')
def lp(request:Request,password:str=Form(...)):
 if hmac.compare_digest(password,os.getenv('APP_PASSWORD','')):request.session['ok']=True;return RedirectResponse('/',303)
 return tpl.TemplateResponse(request=request,name='login.html',context={'error':'Falsches Passwort'},status_code=401)
@app.post('/logout')
def lo(request:Request):request.session.clear();return RedirectResponse('/login',303)
@app.get('/',response_class=HTMLResponse)
def home(request:Request):
 if (x:=guard(request)):return x
 cs=campaigns();ps=crack_points();return tpl.TemplateResponse(request=request,name='home.html',context={'cs':cs,'ps':ps,'text':assessment(cs)})
@app.get('/level',response_class=HTMLResponse)
def ld(request:Request):
 if (x:=guard(request)):return x
 cs=campaigns();chart=[{'date':c['measured_at'],'delta':c['stats']['house']['delta'],'terrace':c['stats']['terrace']['delta'],'groundwater':c['groundwater'],'air_temp':c['air_temp']} for c in cs];return tpl.TemplateResponse(request=request,name='level.html',context={'cs':list(reversed(cs)),'chart':chart,'text':assessment(cs),'settings':settings()})
@app.get('/level/new',response_class=HTMLResponse)
def ln(request:Request):
 if (x:=guard(request)):return x
 with con() as c:dev=[dict(r) for r in c.execute('SELECT * FROM devices WHERE active=1 ORDER BY name')]
 return tpl.TemplateResponse(request=request,name='level_form.html',context={'now':datetime.now().strftime('%Y-%m-%dT%H:%M'),'devices':dev})
@app.post('/level')
def lc(request:Request,measured_at:str=Form(...),air_temp:float|None=Form(None),wall_temp_sw:float|None=Form(None),wall_temp_so:float|None=Form(None),groundwater:float|None=Form(None),rainfall_14d:float|None=Form(None),weather:str=Form(''),light_mode:str=Form(''),notes:str=Form(''),device_id:int|None=Form(None)):
 if (x:=guard(request)):return x
 with con() as c:cid=c.execute('INSERT INTO campaigns(measured_at,air_temp,wall_temp_sw,wall_temp_so,groundwater,rainfall_14d,weather,light_mode,notes,device_id) VALUES(?,?,?,?,?,?,?,?,?,?)',(measured_at,air_temp,wall_temp_sw,wall_temp_so,groundwater,rainfall_14d,weather,light_mode,notes,device_id)).lastrowid
 return RedirectResponse(f'/level/{cid}/readings',303)
@app.get('/level/{cid}/readings',response_class=HTMLResponse)
def lr(request:Request,cid:int):
 if (x:=guard(request)):return x
 return tpl.TemplateResponse(request=request,name='readings.html',context={'cid':cid,'points':POINTS,'g':grouped(cid)})
@app.post('/level/{cid}/readings')
async def lrs(request:Request,cid:int):
 if (x:=guard(request)):return x
 f=await request.form()
 with con() as c:
  c.execute('DELETE FROM readings WHERE campaign_id=?',(cid,))
  for p in POINTS:
   for i,raw in enumerate(f.getlist(p),1):
    raw=str(raw).strip().replace(',','.')
    if raw:c.execute('INSERT INTO readings(campaign_id,point,sequence,value) VALUES(?,?,?,?)',(cid,p,i,float(raw)))
 return RedirectResponse('/level',303)
@app.post('/level/{cid}/photo')
async def lphoto(request:Request,cid:int,point:str=Form(''),caption:str=Form(''),file:UploadFile=File(...)):
 if (x:=guard(request)):return x
 n=photo(await file.read(),file.content_type,f'level-{cid}',LEVEL)
 with con() as c:c.execute('INSERT INTO photos(campaign_id,point,filename,caption) VALUES(?,?,?,?)',(cid,point,n,caption))
 return RedirectResponse('/level',303)
@app.get('/uploads/level/{name}')
def lpic(request:Request,name:str):
 if (x:=guard(request)):return x
 return FileResponse(LEVEL/Path(name).name)
@app.get('/cracks',response_class=HTMLResponse)
def cd(request:Request):
 if (x:=guard(request)):return x
 ps=crack_points();data=[{'name':p['name'],'id':p['id'],'measurements':[{'date':m['measured_at'],'value':m['value'],'delta':m['value']-p['baseline'] if p['baseline'] is not None else None,'temp':m['air_temp']} for m in p['measurements']]} for p in ps];return tpl.TemplateResponse(request=request,name='cracks.html',context={'ps':ps,'data':data})
@app.get('/cracks/new',response_class=HTMLResponse)
def cn(request:Request):
 if (x:=guard(request)):return x
 return tpl.TemplateResponse(request=request,name='crack_form.html',context={})
@app.post('/cracks')
def cc(request:Request,name:str=Form(...),location:str=Form(''),description:str=Form(''),unit:str=Form('mm'),crack_type:str=Form('Sonstiges'),reference_value:float|None=Form(None),warning_delta:float=Form(.3),alarm_delta:float=Form(.5)):
 if (x:=guard(request)):return x
 with con() as c:pid=c.execute('INSERT INTO crack_points(name,location,description,unit,crack_type,reference_value,warning_delta,alarm_delta) VALUES(?,?,?,?,?,?,?,?)',(name,location,description,unit,crack_type,reference_value,warning_delta,alarm_delta)).lastrowid
 return RedirectResponse(f'/cracks/{pid}',303)
@app.get('/cracks/{pid}',response_class=HTMLResponse)
def cdetail(request:Request,pid:int):
 if (x:=guard(request)):return x
 p=crack_point(pid)
 if not p:raise HTTPException(404)
 data=[{'date':m['measured_at'],'value':m['value'],'delta':m['value']-p['baseline'] if p['baseline'] is not None else None,'temp':m['air_temp']} for m in p['measurements']];pics=[m for m in p['measurements'] if m['photo_filename']]
 return tpl.TemplateResponse(request=request,name='crack_detail.html',context={'p':p,'data':data,'first':pics[0] if pics else None,'latest':pics[-1] if pics else None})
@app.get('/cracks/{pid}/new',response_class=HTMLResponse)
def cmn(request:Request,pid:int):
 if (x:=guard(request)):return x
 return tpl.TemplateResponse(request=request,name='crack_measure.html',context={'p':crack_point(pid),'now':datetime.now().strftime('%Y-%m-%dT%H:%M')})
@app.post('/cracks/{pid}/measurements')
async def cmc(request:Request,pid:int,measured_at:str=Form(...),air_temp:float|None=Form(None),value:float=Form(...),notes:str=Form(''),file:UploadFile|None=File(None)):
 if (x:=guard(request)):return x
 n=photo(await file.read(),file.content_type,f'crack-{pid}',CRACK) if file and file.filename else None
 with con() as c:c.execute('INSERT INTO crack_measurements(crack_point_id,measured_at,air_temp,value,notes,photo_filename) VALUES(?,?,?,?,?,?)',(pid,measured_at,air_temp,value,notes,n))
 return RedirectResponse(f'/cracks/{pid}',303)
@app.get('/uploads/cracks/{name}')
def cpic(request:Request,name:str):
 if (x:=guard(request)):return x
 return FileResponse(CRACK/Path(name).name)
@app.get('/cracks/{pid}/qr.png')
def qr(request:Request,pid:int):
 base=settings().get('base_url') or str(request.base_url).rstrip('/');im=qrcode.make(f'{base}/cracks/{pid}/new');b=io.BytesIO();im.save(b,'PNG');return Response(b.getvalue(),media_type='image/png')
@app.get('/admin',response_class=HTMLResponse)
def admin(request:Request):
 if (x:=guard(request)):return x
 with con() as c:dev=[dict(r) for r in c.execute('SELECT * FROM devices ORDER BY name')]
 return tpl.TemplateResponse(request=request,name='admin.html',context={'s':settings(),'devices':dev,'cs':campaigns()})
@app.post('/admin/settings')
async def aset(request:Request):
 if (x:=guard(request)):return x
 f=await request.form()
 with con() as c:
  for k in ['level_reference_id','level_info','level_warning','level_alarm','base_url']:c.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)',(k,str(f.get(k,''))))
 return RedirectResponse('/admin',303)
@app.post('/admin/devices')
def adev(request:Request,name:str=Form(...),kind:str=Form(''),serial:str=Form(''),calibrated_at:str=Form(''),notes:str=Form('')):
 if (x:=guard(request)):return x
 with con() as c:c.execute('INSERT INTO devices(name,kind,serial,calibrated_at,notes) VALUES(?,?,?,?,?)',(name,kind,serial,calibrated_at,notes))
 return RedirectResponse('/admin',303)
@app.get('/exports/nivellement.csv')
def lcsv(request:Request):
 if (x:=guard(request)):return x
 o=io.StringIO();w=csv.writer(o,delimiter=';');w.writerow(['ID','Zeitpunkt','Luft','WandSW','WandSO','Grundwasser','Regen14d','Wetter','Licht','Notiz','Gerät',*[f'{p}{i}' for p in POINTS for i in range(1,6)],'Haus','HausDelta','HausSE','Status','Terrasse','TerrasseDelta'])
 for c in campaigns():
  g=grouped(c['id']);vals=lambda p:g[p]+['']*(5-len(g[p]));w.writerow([c['id'],c['measured_at'],c['air_temp'],c['wall_temp_sw'],c['wall_temp_so'],c['groundwater'],c['rainfall_14d'],c['weather'],c['light_mode'],c['notes'],c['device_name'],*[x for p in POINTS for x in vals(p)],c['stats']['house']['value'],c['stats']['house']['delta'],c['stats']['house']['se'],c['stats']['status'],c['stats']['terrace']['value'],c['stats']['terrace']['delta']])
 return StreamingResponse(iter([o.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=nivellement.csv'})
@app.get('/exports/risse.csv')
def ccsv(request:Request):
 if (x:=guard(request)):return x
 o=io.StringIO();w=csv.writer(o,delimiter=';');w.writerow(['Messstelle','Typ','Ort','Einheit','Warnung','Alarm','Datum','Luft','Messwert','Delta','Notiz','Foto'])
 for p in crack_points(False):
  for m in p['measurements']:w.writerow([p['name'],p['crack_type'],p['location'],p['unit'],p['warning_delta'],p['alarm_delta'],m['measured_at'],m['air_temp'],m['value'],m['value']-p['baseline'] if p['baseline'] is not None else None,m['notes'],m['photo_filename']])
 return StreamingResponse(iter([o.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=risse.csv'})
@app.get('/reports/year/{year}.pdf')
def yearly(request:Request,year:int):
 if (x:=guard(request)):return x
 cs=year_filter(campaigns(),year);ps=crack_points(False)
 for p in ps:p['measurements']=year_filter(p['measurements'],year)
 return StreamingResponse(report(cs,ps,year,LEVEL,CRACK,assessment(cs)),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename=hausmonitor-{year}.pdf'})
@app.get('/reports/all.pdf')
def allpdf(request:Request):
 if (x:=guard(request)):return x
 cs=campaigns();return StreamingResponse(report(cs,crack_points(False),None,LEVEL,CRACK,assessment(cs)),media_type='application/pdf',headers={'Content-Disposition':'attachment; filename=hausmonitor-gesamt.pdf'})
