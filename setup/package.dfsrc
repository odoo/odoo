# Please note that this Dockerfile is used for testing nightly builds and should
# not be used to deploy Odoo
FROM debian:stable
MAINTAINER Odoo S.A. <info@odoo.com>

RUN apt-get update && \
	apt-get install -y locales && \
	rm -rf /var/lib/apt/lists/*

# Reconfigure locales such that postgresql uses UTF-8 encoding
RUN dpkg-reconfigure locales && \
    locale-gen C.UTF-8 && \
    /usr/sbin/update-locale LANG=C.UTF-8
ENV LC_ALL C.UTF-8

RUN apt-get update -qq &&  \
	apt-get upgrade -qq -y && \
	apt-get install \
		postgresql \
		postgresql-server-dev-all \
		postgresql-client \
		adduser \
		libxml2-dev \
		libxslt1-dev \
		libldap2-dev \
		libsasl2-dev \
		libssl-dev \
		libjpeg-dev \
		python-dev \
		python-pip \
		build-essential \
		python -y && \
	easy_install --upgrade pip && \
	rm -rf /var/lib/apt/lists/*

COPY requirements.txt /opt/release/requirements.txt

RUN pip install -r /opt/release/requirements.txt

RUN echo "PS1=\"[\u@nightly-tests] # \"" > ~/.bashrc
