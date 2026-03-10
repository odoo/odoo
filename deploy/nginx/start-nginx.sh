#!/bin/sh
set -eu

DOMAIN="${DOMAIN:-kodoo.online}"
CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
KEY_PATH="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"

if [ -f "$CERT_PATH" ] && [ -f "$KEY_PATH" ]; then
    cp /etc/nginx/templates/kodoo.https.conf /etc/nginx/conf.d/default.conf
    echo "[nginx] TLS certificate found for ${DOMAIN}. Starting in HTTPS mode."
else
    cp /etc/nginx/templates/kodoo.http.conf /etc/nginx/conf.d/default.conf
    echo "[nginx] TLS certificate not found for ${DOMAIN}. Starting in HTTP mode."
    echo "[nginx] Public publishing currently uses Cloudflare Tunnel (make up-tunnel)."
fi

exec nginx -g 'daemon off;'
