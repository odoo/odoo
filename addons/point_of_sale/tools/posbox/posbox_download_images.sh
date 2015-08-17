#!/bin/sh

wget 'http://downloads.raspberrypi.org/raspbian_latest' -O raspbian.img.zip
unzip raspbian.img.zip
wget 'https://github.com/dhruvvyas90/qemu-rpi-kernel/raw/master/kernel-qemu'
