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
		adduser \
		postgresql \
		postgresql-client \
		python \
		python-dateutil \
		python-decorator \
		python-docutils \
		python-feedparser \
		python-imaging \
		python-jinja2 \
		python-ldap \
		python-libxslt1 \
		python-lxml \
		python-mako \
		python-mock \
		python-openid \
		python-passlib \
		python-psutil \
		python-psycopg2 \
		python-pybabel \
		python-pychart \
		python-pydot \
		python-pyparsing \
		python-pypdf \
		python-reportlab \
		python-requests \
		python-simplejson \
		python-tz \
		python-unittest2 \
		python-vatnumber \
		python-vobject \
		python-werkzeug \
		python-xlwt \
		python-yaml -y && \
	rm -rf /var/lib/apt/lists/*

RUN echo "PS1=\"[\u@nightly-tests] # \"" > ~/.bashrc
