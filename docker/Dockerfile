FROM debian:12-slim

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    automake \
    autoconf \
    libtool \
    pkg-config \
    libpng-dev \
    libjpeg-dev \
    zlib1g-dev \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy CCV library source from parent directory
COPY ../lib /app/ccv/lib
COPY ../samples /app/ccv/samples

# Build CCV library
WORKDIR /app/ccv/lib
RUN ./configure && make clean && make -j$(nproc)

# Build swtdetect binary
WORKDIR /app/ccv/bin
COPY docker/swtdetect.c ./
RUN gcc -o swtdetect swtdetect.c \
    -I../lib -L../lib -lccv \
    -lpng -ljpeg -lz -lm -lpthread \
    -O2 -D HAVE_LIBPNG -D HAVE_LIBJPEG

# Setup Python environment
WORKDIR /app
RUN python3 -m venv venv
COPY docker/requirements.txt .
RUN . venv/bin/activate && pip install --no-cache-dir -r requirements.txt

# Copy API service and configuration files
COPY docker/api_service.py .
COPY docker/nginx.conf /etc/nginx/
COPY docker/supervisord.conf /etc/supervisor/conf.d/

# Create necessary directories
RUN mkdir -p /app/uploads /app/results /var/log/supervisor

# Expose ports
EXPOSE 80 443

# Start services via supervisor
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]