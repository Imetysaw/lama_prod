# LaMa frontend: Angular app served by nginx, which also proxies /api to the backend
# and (in production) terminates HTTPS.

# Stage 1 [Build the app]
# Angular 13 only supports Node <= 16. This stage is only used to build the static
# files; it is not part of the final image.
FROM node:16.20.2-alpine AS build

WORKDIR /usr/local/app

# Install dependencies first (cached as long as the package files do not change)
COPY ./frontend/package.json ./frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY ./frontend/ ./

# URL under which the browser reaches the API. In the docker setups nginx proxies
# /api to the backend, so the frontend and API share one origin (no CORS, no mixed content).
ARG API_URL=/api
ENV API_URL=${API_URL} \
    PROD_API_URL=${API_URL}

RUN npm run build

# Stage 2 [nginx for serving the app and proxying the API]
FROM nginx:1.28-alpine

# Remove the default site; 40-lama-config.sh writes the LaMa config on startup
RUN rm -f /etc/nginx/conf.d/default.conf \
    && mkdir -p /var/www/certbot /etc/nginx/lama

COPY ./frontend/nginx/*.conf ./frontend/nginx/*.template /etc/nginx/lama/
COPY --chmod=755 ./frontend/nginx/40-lama-config.sh /docker-entrypoint.d/40-lama-config.sh

COPY --from=build /usr/local/app/dist/webapp /usr/share/nginx/html

EXPOSE 80 443
