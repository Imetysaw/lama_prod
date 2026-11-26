#!/bin/sh
# Obtains a Let's Encrypt certificate for $DOMAIN (HTTP-01 challenge via the
# webroot served by nginx) and then tries to renew it every 12 hours.
# certbot only actually renews when the certificate expires within 30 days.
set -u

if [ "${NGINX_MODE:-https}" != "https" ]; then
    echo "certbot: NGINX_MODE=${NGINX_MODE}, HTTPS disabled - nothing to do"
    while :; do sleep 86400; done
fi

if [ -z "${CERTBOT_EMAIL:-}" ] || echo "$CERTBOT_EMAIL" | grep -q CHANGE_ME; then
    echo "certbot: set CERTBOT_EMAIL in .env.prod" >&2
    exit 1
fi

WEBROOT=/var/www/certbot
STAGING=""
if [ "${CERTBOT_STAGING:-0}" = "1" ]; then
    STAGING="--staging"
    echo "certbot: using the Let's Encrypt STAGING environment"
fi

# Give nginx a moment to start serving the challenge directory
sleep 10

until [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; do
    echo "certbot: requesting certificate for ${DOMAIN}"
    if ! certbot certonly --webroot -w "$WEBROOT" \
        -d "$DOMAIN" --email "$CERTBOT_EMAIL" \
        --agree-tos --no-eff-email --non-interactive \
        --cert-name "$DOMAIN" $STAGING; then
        # Stay well below Let's Encrypt's limit of 5 failed validations per hour
        echo "certbot: failed - check that ${DOMAIN} points to this server and port 80 is reachable. Retrying in 15 minutes." >&2
        sleep 900
    fi
done

echo "certbot: certificate present, checking for renewal every 12 hours"
while :; do
    certbot renew --webroot -w "$WEBROOT" --non-interactive || echo "certbot: renewal attempt failed" >&2
    sleep 43200
done
