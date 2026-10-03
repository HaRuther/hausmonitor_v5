from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image as RImage

def f(v,n=3):return '–' if v is None else f'{v:.{n}f}'
def t(rows,widths):
 x=Table(rows,repeatRows=1,colWidths=widths);x.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#17365d')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.25,colors.grey),('FONTSIZE',(0,0),(-1,-1),8),('VALIGN',(0,0),(-1,-1),'TOP')]));return x
def report(level,cracks,year=None,level_dir=None,crack_dir=None,assessment=''):
 b=BytesIO();d=SimpleDocTemplate(b,pagesize=A4,rightMargin=12*mm,leftMargin=12*mm,topMargin=12*mm,bottomMargin=12*mm);s=getSampleStyleSheet();title=f'Hausmonitor Jahresbericht {year}' if year else 'Hausmonitor Gesamtbericht';story=[Paragraph(title,s['Title']),Paragraph('Monitoring-Dokumentation; kein statischer oder geotechnischer Nachweis.',s['BodyText']),Spacer(1,4*mm),Paragraph('Automatische Lagebeurteilung',s['Heading2']),Paragraph(assessment,s['BodyText']),Spacer(1,4*mm),Paragraph('Nivellement',s['Heading2'])]
 rows=[['Datum','Haus','Δ','SE','Status','Terrasse','GW','Gerät']]
 for c in level:rows.append([c['measured_at'].replace('T',' '),f(c['stats']['house']['value']),f(c['stats']['house']['delta']),f(c['stats']['house']['se']),c['stats']['status'],f(c['stats']['terrace']['value']),f(c['groundwater']),c.get('device_name') or '–'])
 story.append(t(rows,[32*mm,18*mm,17*mm,16*mm,20*mm,20*mm,17*mm,30*mm]));story.append(PageBreak());story.append(Paragraph('Rissmonitoring',s['Heading2']))
 for i,p in enumerate(cracks):
  story.append(Paragraph(f"{p['name']} – {p['status']}",s['Heading3']));story.append(Paragraph(f"Typ: {p['crack_type']} · Ort: {p['location'] or '–'} · Änderung: {f(p['delta'])} {p['unit']}",s['BodyText']))
  rows=[['Datum','Temp.','Messwert','Δ','Notiz']]
  for m in p['measurements']:rows.append([m['measured_at'].replace('T',' '),f(m['air_temp'],1),f(m['value']),f(m['value']-p['baseline'] if p['baseline'] is not None else None),m['notes'] or ''])
  story.append(t(rows,[38*mm,22*mm,25*mm,23*mm,65*mm]))
  pics=[m for m in p['measurements'] if m['photo_filename']]
  if pics and crack_dir:
   for label,m in [('Erstes Foto',pics[0]),('Aktuelles Foto',pics[-1])]:
    q=crack_dir/m['photo_filename']
    if q.exists():story+=[Paragraph(label,s['Heading4']),RImage(str(q),width=75*mm,height=55*mm,kind='proportional')]
  if i<len(cracks)-1:story.append(Spacer(1,5*mm))
 d.build(story);b.seek(0);return b
