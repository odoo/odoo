#!/bin/sh

wget 'https://downloads.raspberrypi.org/raspbian_lite_latest' -O raspbian.img.zip
unzip raspbian.img.zip
wget 'https://github.com/dhruvvyas90/qemu-rpi-kernel/raw/master/kernel-qemu-4.1.13-jessie' -O kernel-qemu
