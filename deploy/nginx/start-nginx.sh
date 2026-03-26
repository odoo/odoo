#!/bin/sh
set -eu

DOMAIN="${DOMAIN:-kodoo.online}"
WILDCARD_DOMAIN="*.${DOMAIN}"
ROOT_DB="${PROD_DB_NAME:-kodoo}"
CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
KEY_PATH="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"

render_template() {
    template_path="$1"
    sed \
        -e "s|__DOMAIN__|${DOMAIN}|g" \
        -e "s|__WILDCARD_DOMAIN__|${WILDCARD_DOMAIN}|g" \
        -e "s|__ROOT_DB__|${ROOT_DB}|g" \
        "$template_path" > /etc/nginx/conf.d/default.conf
}

if [ -f "$CERT_PATH" ] && [ -f "$KEY_PATH" ]; then
    render_template /etc/nginx/templates/kodoo.https.conf
    echo "[nginx] TLS certificate found for ${DOMAIN}. Starting in HTTPS mode."
else
    render_template /etc/nginx/templates/kodoo.http.conf
    echo "[nginx] TLS certificate not found for ${DOMAIN}. Starting in HTTP mode."
    echo "[nginx] Public publishing currently uses Cloudflare Tunnel (make up-tunnel)."
fi

exec nginx -g 'daemon off;'
