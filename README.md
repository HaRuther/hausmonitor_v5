# Hausmonitor V5

Vollständige Zusammenführung aller bisherigen Funktionen plus Grenzwerte, Referenzwahl, Geräteverwaltung, automatische Lagebeurteilung, Rissarten, Vorher/Nachher-Fotos, kombinierte Diagramme, Jahresberichte und QR-Codes.

## Update

```bash
cd /root/hausmonitor
./scripts/backup.sh || true
cp -a data /root/hausmonitor-data-backup
cp .env /root/hausmonitor-env-backup
docker-compose down
```

Neue Projektdateien einspielen, danach die gesicherten Ordner `data/` und `.env` übernehmen:

```bash
cd /root/hausmonitor
docker-compose up -d --build
docker ps
docker logs --tail=100 hausmonitor-v5
```

Die bestehende SQLite-Datenbank wird ausschließlich additiv erweitert.

## Funktionen

- vollständiges Nivellement mit Haus, Terrasse, Anbau, Statistik, Fotos, CSV und PDF
- Rissmonitoring mit Fotos, Temperatur, Rissart, Grenzwerten, CSV und PDF
- frei wählbare Referenzkampagne und globale Nivellement-Grenzwerte
- Geräte- und Kalibrierverwaltung
- automatische textliche Lagebeurteilung
- erstes und aktuelles Rissfoto nebeneinander
- QR-Code je Rissmessstelle
- Jahres- und Gesamtberichte
- PWA-App-Shell und Docker-Betrieb
- Backup-Skript

## QR-Code

Unter Einstellungen eine aus dem Smartphone erreichbare Basis-URL eintragen, zum Beispiel `http://192.168.2.62:8000`. Der QR-Code führt direkt zur Eingabe einer neuen Messung.

## App-Icon

Das Paket enthält das Hausmonitor-App-Icon als PWA-Icons in 192 und 512 Pixeln, Apple-Touch-Icon sowie Browser-Favicons.
