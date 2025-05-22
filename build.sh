#!/usr/bin/env bash
apt-get update -o Acquire::Check-Valid-Until=false && apt-get upgrade -y
apt-get install -y \
    gcc \
    libldap2-dev \
    libsasl2-dev
