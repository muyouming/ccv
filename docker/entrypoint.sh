#!/bin/bash
set -e

# Check if CCV library needs to be built
if [ ! -f /app/ccv/lib/libccv.a ]; then
    echo "Building CCV library..."
    cd /app/ccv/lib
    ./configure
    make clean
    make -j$(nproc)
    
    echo "Building swtdetect binary..."
    cd /app/ccv/bin
    gcc -o swtdetect swtdetect.c \
        -I../lib -L../lib -lccv \
        -lpng -ljpeg -lz -lm -lpthread \
        -O2 -D HAVE_LIBPNG -D HAVE_LIBJPEG
    
    echo "Build complete!"
fi

# Execute the main command
exec "$@"