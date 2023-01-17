FROM ubuntu:20.04 
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt install -y python3-pip libldap2-dev libpq-dev libsasl2-dev nodejs npm
RUN mkdir /opt/odoo
COPY . /opt/odoo/
RUN pip3 install setuptools wheel
RUN pip3 install -r /opt/odoo/requirements.txt
ENTRYPOINT [ "python3", "/opt/odoo/odoo-bin" ]
