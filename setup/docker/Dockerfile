FROM debian:wheezy
MAINTAINER Odoo S.A. <info@odoo.com>

# Change policy-rc.d so that services start automatically once installed
RUN echo "#!/bin/sh\nexit 0" > /usr/sbin/policy-rc.d

RUN apt-get update && \
	apt-get install -y \
		ca-certificates \
		locales \
		wget && \
	rm -rf /var/lib/apt/lists/*

# Reconfigure locales such that postgresql uses UTF-8 encoding
RUN dpkg-reconfigure locales && \
    locale-gen C.UTF-8 && \
    /usr/sbin/update-locale LANG=C.UTF-8
ENV LC_ALL C.UTF-8

# Install lessc and less-plugin-clean-css
RUN wget -O - https://deb.nodesource.com/setup | bash -
RUN apt-get -y install nodejs
RUN npm install -g less less-plugin-clean-css

# Install wkhtmltopdf
RUN wget http://downloads.sourceforge.net/project/wkhtmltopdf/0.12.1/wkhtmltox-0.12.1_linux-wheezy-amd64.deb && \
	dpkg --force-depends -i wkhtmltox-0.12.1_linux-wheezy-amd64.deb && \
	apt-get -y install -f && \
	rm -f wkhtmltox-0.12.1_linux-wheezy-amd64.deb 

# Retrieve Odoo public key, add Odoo nightly to repo list and install Odoo
RUN wget -O - https://nightly.odoo.com/odoo.key | apt-key add -
RUN echo "deb http://nightly.odoo.com/8.0/nightly/deb/ ./" >> /etc/apt/sources.list
RUN apt-get update && \
	apt-get -y install odoo && \
	rm -rf /var/lib/apt/lists/*

# Run script
COPY run.sh /run.sh
RUN chmod u+x /run.sh

CMD ["/run.sh"]