#!/bin/bash

if [ "$EUID" -ne 0 ]
then
    echo "This script requires root privileges in order to access /usr/local/bin."
    exit 1
fi

MKCASTPATH="$(pwd)/mkcast"
NEWCASTPATH="$(pwd)/newcast"

cd /usr/local/bin
ln -s $MKCASTPATH mkcast
ln -s $NEWCASTPATH newcast
