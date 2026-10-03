import os,sqlite3
from contextlib import contextmanager
from pathlib import Path
DB=Path(os.getenv('DATABASE_PATH','/data/hausmonitor.db'));UPLOAD=Path(os.getenv('UPLOAD_DIR','/data/uploads'));LEVEL=UPLOAD/'level';CRACK=UPLOAD/'cracks'
SCHEMA='''
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
CREATE TABLE IF NOT EXISTS devices(id INTEGER PRIMARY KEY,name TEXT NOT NULL,kind TEXT,serial TEXT,calibrated_at TEXT,notes TEXT,active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS campaigns(id INTEGER PRIMARY KEY,measured_at TEXT NOT NULL,air_temp REAL,wall_temp_sw REAL,wall_temp_so REAL,groundwater REAL,rainfall_14d REAL,weather TEXT,light_mode TEXT,notes TEXT,device_id INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(device_id) REFERENCES devices(id));
CREATE TABLE IF NOT EXISTS readings(id INTEGER PRIMARY KEY,campaign_id INTEGER NOT NULL,point TEXT NOT NULL,sequence INTEGER NOT NULL,value REAL NOT NULL,UNIQUE(campaign_id,point,sequence),FOREIGN KEY(campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS photos(id INTEGER PRIMARY KEY,campaign_id INTEGER NOT NULL,point TEXT,filename TEXT NOT NULL,caption TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS crack_points(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,location TEXT,description TEXT,unit TEXT DEFAULT 'mm',crack_type TEXT DEFAULT 'Sonstiges',reference_value REAL,warning_delta REAL DEFAULT .3,alarm_delta REAL DEFAULT .5,active INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS crack_measurements(id INTEGER PRIMARY KEY,crack_point_id INTEGER NOT NULL,measured_at TEXT NOT NULL,air_temp REAL,value REAL NOT NULL,notes TEXT,photo_filename TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(crack_point_id) REFERENCES crack_points(id) ON DELETE CASCADE);
'''
def init_db():
 DB.parent.mkdir(parents=True,exist_ok=True);LEVEL.mkdir(parents=True,exist_ok=True);CRACK.mkdir(parents=True,exist_ok=True)
 with sqlite3.connect(DB) as c:
  c.execute('PRAGMA foreign_keys=ON');c.executescript(SCHEMA)
  defaults={'level_reference_id':'','level_info':'1.0','level_warning':'3.0','level_alarm':'5.0','base_url':''}
  for k,v in defaults.items():c.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)',(k,v))
  # additive migrations from V3/V4
  migrations={'campaigns':[('rainfall_14d','REAL'),('light_mode','TEXT'),('device_id','INTEGER')],'crack_points':[('crack_type',"TEXT DEFAULT 'Sonstiges'"),('warning_delta','REAL DEFAULT .3'),('alarm_delta','REAL DEFAULT .5')]}
  for table,cols in migrations.items():
   have={r[1] for r in c.execute(f'PRAGMA table_info({table})')}
   for name,typ in cols:
    if name not in have:c.execute(f'ALTER TABLE {table} ADD COLUMN {name} {typ}')
@contextmanager
def con():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
 try:yield c;c.commit()
 finally:c.close()
def settings():
 with con() as c:return {r['key']:r['value'] for r in c.execute('SELECT * FROM settings')}
