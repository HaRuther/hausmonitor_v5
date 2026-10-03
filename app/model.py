from math import sqrt
from statistics import mean,stdev
from datetime import datetime
from .database import con,settings
POINTS=('SW','SO','ANB','TSW','TSO')
def summary(v):
 if not v:return {'n':0,'mean':None,'sd':None,'se':None}
 sd=stdev(v) if len(v)>1 else None;return {'n':len(v),'mean':mean(v),'sd':sd,'se':sd/sqrt(len(v)) if sd is not None else None}
def grouped(cid):
 g={p:[] for p in POINTS}
 with con() as c:
  for r in c.execute('SELECT point,value FROM readings WHERE campaign_id=? ORDER BY sequence',(cid,)):g.setdefault(r['point'],[]).append(r['value'])
 return g
def pair(a,b,base):
 if a['mean'] is None or b['mean'] is None:return {'value':None,'se':None,'delta':None,'snr':None}
 value=b['mean']-a['mean'];se=sqrt(a['se']**2+b['se']**2) if a['se'] is not None and b['se'] is not None else None;delta=value-base if base is not None else None
 return {'value':value,'se':se,'delta':delta,'snr':abs(delta)/se if delta is not None and se else None}
def level_status(delta,s):
 if delta is None:return ('Keine Referenz','neutral')
 a=abs(delta);alarm=float(s.get('level_alarm',5));warn=float(s.get('level_warning',3));info=float(s.get('level_info',1))
 return ('Alarm','alarm') if a>=alarm else ('Warnung','warning') if a>=warn else ('Beobachten','info') if a>=info else ('Stabil','ok')
def campaigns():
 with con() as c:rows=[dict(r) for r in c.execute('SELECT campaigns.*,devices.name device_name FROM campaigns LEFT JOIN devices ON devices.id=campaigns.device_id ORDER BY measured_at,id')]
 if not rows:return []
 s=settings();refid=int(s['level_reference_id']) if s.get('level_reference_id','').isdigit() else rows[0]['id'];raw={r['id']:grouped(r['id']) for r in rows};refs={}
 for key,a,b in [('house','SW','SO'),('terrace','TSW','TSO')]:
  rr=raw.get(refid,raw[rows[0]['id']]);sa,sb=summary(rr.get(a,[])),summary(rr.get(b,[]));refs[key]=sb['mean']-sa['mean'] if sa['mean'] is not None and sb['mean'] is not None else None
 out=[]
 for r in rows:
  st={p:summary(raw[r['id']].get(p,[])) for p in POINTS};st['house']=pair(st['SW'],st['SO'],refs['house']);st['terrace']=pair(st['TSW'],st['TSO'],refs['terrace']);st['status'],st['status_class']=level_status(st['house']['delta'],s);st['reference_id']=refid;r['stats']=st;out.append(r)
 return out
def crack_points(active=True):
 with con() as c:
  rows=[dict(r) for r in c.execute('SELECT * FROM crack_points '+('WHERE active=1 ' if active else '')+'ORDER BY name')]
  for p in rows:
   ms=[dict(r) for r in c.execute('SELECT * FROM crack_measurements WHERE crack_point_id=? ORDER BY measured_at,id',(p['id'],))];p['measurements']=ms;p['baseline']=ms[0]['value'] if ms else p['reference_value'];p['latest']=ms[-1] if ms else None;p['delta']=p['latest']['value']-p['baseline'] if p['latest'] and p['baseline'] is not None else None
   a=abs(p['delta']) if p['delta'] is not None else 0;p['status'],p['status_class']=(('Alarm','alarm') if a>=p['alarm_delta'] else ('Warnung','warning') if a>=p['warning_delta'] else ('Stabil','ok'))
 return rows
def crack_point(pid):return next((p for p in crack_points(False) if p['id']==pid),None)
def regression(xs,ys):
 p=[(float(x),float(y)) for x,y in zip(xs,ys) if x is not None and y is not None]
 if len(p)<3:return None
 mx=mean(x for x,_ in p);my=mean(y for _,y in p);den=sum((x-mx)**2 for x,_ in p)
 if not den:return None
 slope=sum((x-mx)*(y-my) for x,y in p)/den;inter=my-slope*mx;tot=sum((y-my)**2 for _,y in p);res=sum((y-(inter+slope*x))**2 for x,y in p)
 return {'n':len(p),'slope':slope,'intercept':inter,'r2':1-res/tot if tot else None}
def assessment(cs):
 if not cs:return 'Noch keine Nivellement-Messungen vorhanden.'
 x=cs[-1];d=x['stats']['house']['delta'];state=x['stats']['status'];trend=regression(range(len(cs)),[c['stats']['house']['delta'] for c in cs]);t='Für einen linearen Trend sind mindestens drei Kampagnen erforderlich.' if not trend else f"Der lineare Trend beträgt {trend['slope']:+.3f} mm je Kampagne (R² {trend['r2']:.2f})."
 return f"Status: {state}. Die Hausdifferenz hat sich gegenüber der gewählten Referenz um {d:+.3f} mm verändert. {t}" if d is not None else t
def year_filter(items,year):return [x for x in items if str(x.get('measured_at','')).startswith(str(year))]
