#!/bin/sh
set -eu
mkdir -p backups
stamp=$(date +%Y%m%d-%H%M%S)
tar -czf backups/hausmonitor-v5-$stamp.tar.gz data .env
find backups -type f -mtime +90 -delete
