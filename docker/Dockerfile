FROM ubuntu:20.04

# variables & locales
ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update -qq \
    && apt-get upgrade -y\
    && apt-get install -y locales -qq \
    && locale-gen en_US.UTF-8 \
    && dpkg-reconfigure locales \
    && dpkg-reconfigure locales \
    && /usr/sbin/update-locale LANG=en_US.UTF-8 \
    && rm -rf /var/lib/apt/lists/*
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8
ENV LC_ALL en_US.UTF-8

# dependencies for odoo or python packages
RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends python3 python3-pip python3-dev libjpeg-dev libsasl2-dev libxslt-dev libxml2-dev ca-certificates \
    curl file xfonts-75dpi xfonts-base unzip build-essential fontconfig libfontconfig1 libpng16-16 \
    libldap2-dev libssl-dev poppler-utils ttf-dejavu cabextract libfreetype6 python3-magic git libffi-dev libc6 \
    libstdc++6 lib32z1 libpoppler-cpp-dev pkg-config librdkafka-dev python3-cairocffi node-less libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# wkhtmltopdf
RUN curl -sL -o /tmp/wkhtmltox.deb https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.5/wkhtmltox_0.12.5-1.focal_amd64.deb \
    && echo 'ae4e85641f004a2097621787bf4381e962fb91e1 /tmp/wkhtmltox.deb' | sha1sum -c - \
    && apt-get install -y --no-install-recommends /tmp/wkhtmltox.deb \
    && rm -rf /tmp/wkhtmltox.deb

# ghostscript
RUN curl -sL -o /tmp/ghostscript-9.56.1-linux-x86_64.tgz https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs9561/ghostscript-9.56.1-linux-x86_64.tgz \
    && tar -xzf /tmp/ghostscript-9.56.1-linux-x86_64.tgz -C /tmp \
    && mv /tmp/ghostscript-9.56.1-linux-x86_64/gs-9561-linux-x86_64 /usr/local/bin/ghostscript \
    && ln -s /usr/local/bin/ghostscript /usr/local/bin/gs \
    && chmod 755 /usr/local/bin/ghostscript \
    && chmod 755 /usr/local/bin/gs \
    && rm -rf /tmp/ghostscript-9.56.1-linux-x86_64.tgz /tmp/ghostscript-9.56.1-linux-x86_64

# odoo directories
RUN useradd -s /usr/bin/nologin --create-home --password odoo odoo \
  && mkdir --parents /opt/odoo/tests \
  && chown --recursive odoo:odoo /opt/odoo/tests

# msfonts
COPY docker/msfonts.sh /tmp/msfonts.sh
RUN chmod +x /tmp/msfonts.sh; sync; /tmp/msfonts.sh; rm -rf /tmp/msfonts.sh

# pip dependencies
COPY requirements.txt /tmp/requirements.txt
# 2to3 was removed from setuptools v58.0.0 which will break the build
# https://setuptools.readthedocs.io/en/latest/history.html#breaking-changes
RUN pip3 install --no-cache-dir setuptools --upgrade \
    && pip3 install --no-cache-dir --upgrade pip \
    && pip3 install --no-cache-dir -r /tmp/requirements.txt \
    && rm -rf /tmp/requirements.txt

RUN apt-get purge -y build-essential

WORKDIR /opt/odoo
COPY --chown=odoo:odoo . .

EXPOSE 8069 8072
USER odoo
