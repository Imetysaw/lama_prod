#!/bin/sh
# Runs on container start (via the nginx image's /docker-entrypoint.d mechanism).
#
# NGINX_MODE=http  : serve over plain HTTP (development, or behind another TLS proxy)
# NGINX_MODE=https : serve over HTTPS with the Let's Encrypt certificate for $DOMAIN.
#                    Until certbot has obtained the certificate, plain HTTP is served
#                    (so the ACME challenge can be answered). A background loop switches
#                    to HTTPS as soon as the certificate exists, and reloads nginx every
#                    6 hours so renewed certificates are picked up.
set -eu

MODE="${NGINX_MODE:-http}"
DOMAIN="${DOMAIN:-localhost}"
export DOMAIN
CONF=/etc/nginx/conf.d/default.conf
CERT="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"

write_conf() {
    envsubst '${DOMAIN}' < "/etc/nginx/lama/lama-$1.conf.template" > "$CONF"
    echo "lama: using $1 configuration for ${DOMAIN}"
}

if [ "$MODE" != "https" ]; then
    write_conf http
    exit 0
fi

if [ "$DOMAIN" = "localhost" ]; then
    echo "lama: NGINX_MODE=https requires DOMAIN to be set" >&2
    exit 1
fi

if [ -f "$CERT" ]; then
    write_conf https
else
    echo "lama: no certificate for ${DOMAIN} yet, serving HTTP until certbot has obtained one"
    write_conf http
fi

# Background watcher: switch to HTTPS once the certificate appears, and reload
# periodically to pick up renewed certificates.
(
    elapsed=0
    while :; do
        sleep 60
        elapsed=$((elapsed + 60))
        if [ -f "$CERT" ] && ! grep -q "listen       443" "$CONF"; then
            write_conf https
            nginx -s reload && echo "lama: switched to HTTPS"
        elif [ "$elapsed" -ge 21600 ]; then
            elapsed=0
            nginx -s reload && echo "lama: reloaded nginx to pick up renewed certificates"
        fi
    done
) &
