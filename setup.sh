#!/bin/bash

if [ "$EUID" -ne 0 ]
then
    echo "This script requires root privileges in order to access /usr/local/bin."
    exit 1
fi

ln -s mkcast /usr/local/bin/mkcast
ln -s newcast /usr/local/bin/newcast
