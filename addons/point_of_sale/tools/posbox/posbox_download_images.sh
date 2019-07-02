#!/bin/sh

wget 'http://downloads.raspberrypi.org/raspbian_lite/images/raspbian_lite-2019-06-24/2019-06-20-raspbian-buster-lite.zip' -O raspbian.img.zip
unzip raspbian.img.zip
wget 'https://github.com/dhruvvyas90/qemu-rpi-kernel/raw/master/kernel-qemu-4.14.79-stretch' -O kernel-qemu
wget 'https://github.com/dhruvvyas90/qemu-rpi-kernel/raw/master/versatile-pb.dtb'

