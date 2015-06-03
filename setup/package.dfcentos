# Please note that this Dockerfile is used for testing nightly builds and should
# not be used to deploy Odoo
FROM centos:centos7
MAINTAINER Odoo S.A. <info@odoo.com>

# Dependencies and postgres
RUN yum install -d 0 -e 0 epel-release -y && \
 	yum update -d 0 -e 0 -y && \
	yum install -d 0 -e 0 \
		babel \
		libxslt-python \
		pychart \
		pyparsing \
		python-dateutil \
		python-decorator \
		python-docutils \
		python-feedparser \
		python-imaging \
		python-jinja2 \
		python-ldap \
		python-lxml \
		python-mako \
		python-mock \
		python-openid \
		python-passlib \
		python-psutil \
		python-psycopg2 \
		python-reportlab \
		python-requests \
		python-simplejson \
		python-unittest2 \
		python-vobject \
		python-werkzeug \
		python-yaml \
		pytz \
		postgresql \
		postgresql-server \
		postgresql-libs \
		postgresql-contrib \
		postgresql-devel -y && \
	yum clean all

RUN easy_install pyPdf vatnumber pydot psycogreen

# Postgres configuration
RUN mkdir -p /var/lib/postgres/data
RUN chown -R postgres:postgres /var/lib/postgres/data
RUN su postgres -c "initdb -D /var/lib/postgres/data -E UTF-8"
RUN cp /usr/share/pgsql/postgresql.conf.sample /var/lib/postgres/data/postgresql.conf

RUN echo "PS1=\"[\u@nightly-tests] # \"" > ~/.bashrc
