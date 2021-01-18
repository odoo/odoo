#!/bin/bash

#  && git clone https://github.com/aws/efs-utils efs/ \
  cd efs/ \
  && ./build-deb.sh \
  && apt-get -y install ./build/amazon-efs-utils*deb \
  && mkdir /mnt/filestore \
  && mount -t nfs4 172.31.35.116:/ /mnt/filestore \
  && mkdir /mnt/config \
  && chown -R odooaurqa /mnt/filestore \
  && mount -t nfs4 172.31.46.245:/ /mnt/config \
  && chown -R odooaurqa /mnt/config