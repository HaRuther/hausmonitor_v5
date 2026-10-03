import os
os.environ['DATABASE_PATH']='/tmp/hm5.db';os.environ['UPLOAD_DIR']='/tmp/hm5up';os.environ['APP_PASSWORD']=''
from fastapi.testclient import TestClient
from app.main import app
from app.database import DB

def setup_module():
 try:DB.unlink()
 except:pass
def test_complete():
 with TestClient(app) as c:
  assert c.get('/health').json()['version']=='5.0.0'
  r=c.post('/level',data={'measured_at':'2026-10-02T10:00'},follow_redirects=False);cid=r.headers['location'].split('/')[2]
  c.post(f'/level/{cid}/readings',data={'SW':['2.575']*5,'SO':['8.270']*5})
  assert c.get('/exports/nivellement.csv').status_code==200
  r=c.post('/cracks',data={'name':'R1','crack_type':'Putzriss','warning_delta':'.3','alarm_delta':'.5'},follow_redirects=False);pid=r.headers['location'].split('/')[2]
  c.post(f'/cracks/{pid}/measurements',data={'measured_at':'2026-10-02T11:00','value':'.5'})
  c.post(f'/cracks/{pid}/measurements',data={'measured_at':'2026-10-03T11:00','value':'.9'})
  assert 'Warnung' in c.get(f'/cracks/{pid}').text
  assert c.get(f'/cracks/{pid}/qr.png').status_code==200
  assert c.get('/exports/risse.csv').status_code==200
  assert c.get('/reports/all.pdf').content[:4]==b'%PDF'
