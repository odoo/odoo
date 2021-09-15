FROM alpine:3.14
MAINTAINER Camptocamp

# create the working directory and a place to set the logs (if wanted)
RUN mkdir -p /odoo /var/log/odoo

COPY ./requirements.txt /odoo

# Moved because there was a bug while installing `odoo-autodiscover`. There is
# an accent in the contributor name
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# build and dev packages
ENV BUILD_PACKAGE \
    build-essential \
    gcc \
    python3.9-dev \
    libevent-dev \
    libfreetype6-dev \
    libxml2-dev \
    libxslt1-dev \
    libsasl2-dev \
    libldap2-dev \
    libssl-dev \
    libjpeg-dev \
    libpng-dev \
    zlib1g-dev \
    git

# Install some deps, lessc and less-plugin-clean-css, and wkhtmltopdf
RUN set -x; \
        apk add --no-cache python3 py3-pip \
        && python3 -m pip install --force-reinstall pip setuptools \
        && pip install -r /odoo/requirements.txt --ignore-installed

# grab gosu for easy step-down from root and dockerize to generate template and
# wait on postgres
# RUN /install/gosu.sh && /install/dockerize.sh


# Expose Odoo services
EXPOSE 8069 8072



ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["odoo"]