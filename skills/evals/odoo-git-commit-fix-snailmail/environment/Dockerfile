# Derived from runbot's "DockerDefault" (odoo/runbot, runbot/data/dockerfile_data.xml),
# pinned to the 20.0 branch. Layers that ship amd64-only debs (wkhtmltopdf, chrome)
# and the npm lint tools are left out: the task needs git and the Odoo Python
# dependencies, not a browser. Harbor's agent installers add nodejs/npm as root.
FROM ubuntu:noble

ENV LANG C.UTF-8
USER root

# runbot: base debian packages
RUN set -x ; \
    apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends apt-transport-https build-essential ca-certificates curl faketime file fonts-freefont-ttf fonts-noto-cjk gawk gnupg gsfonts libldap2-dev libjpeg9-dev libsasl2-dev libxslt1-dev lsb-release npm ocrmypdf sed sudo unzip xfonts-75dpi zip zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# runbot: python debian packages
RUN set -x ; \
    apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends publicsuffix python3 flake8 python3-dbfread python3-dev python3-gevent python3-pip python3-setuptools python3-wheel python3-markdown python3-mock python3-phonenumbers python3-websocket python3-google-auth libpq-dev pylint python3-jwt python3-asn1crypto python3-html2text python3-suds python3-xmlsec python3-markdown2 python3-aiosmtpd python3-paramiko \
    && rm -rf /var/lib/apt/lists/*

# runbot: the branch's debian/control dependencies, with the latest postgresql-client
ADD https://raw.githubusercontent.com/odoo/odoo/20.0/debian/control /tmp/control.txt
RUN curl -sSL https://www.postgresql.org/media/keys/ACCC4CF8.asc -o /etc/apt/trusted.gpg.d/psql_client.asc \
    && echo "deb http://apt.postgresql.org/pub/repos/apt/ `lsb_release -s -c`-pgdg main" > /etc/apt/sources.list.d/pgclient.list \
    && apt-get update \
    && sed -n '/^Depends:/,/^[A-Z]/p' /tmp/control.txt \
        | awk '/^ [a-z]/ { gsub(/,/,"") ; gsub(" ", "") ; print $NF }' | sort -u \
        | DEBIAN_FRONTEND=noninteractive xargs apt-get install -y -qq --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# task: git for the agent, ripgrep for the codex installer, uv for the verifier (rewardkit)
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends git ripgrep \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

# runbot: drop noble's default uid-1000 user, create ours
RUN deluser ubuntu
RUN groupadd -g 1000 odoo && useradd --create-home -u 1000 -g odoo -G audio,video odoo
RUN mkdir /app && chown odoo:odoo /app

USER odoo
ENV PIP_BREAK_SYSTEM_PACKAGES=1

# runbot: external_dependencies and the branch's requirements.txt
RUN python3 -m pip install --no-cache-dir ebaysdk==2.1.5 pdf417gen==0.7.1
ADD --chown=odoo https://raw.githubusercontent.com/odoo/odoo/20.0/requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /tmp/requirements.txt

# task: the developer's identity and a checkout at the base commit, on a dev branch.
# Only the base commit and some history are fetched, so the merged fix and its
# message are not in the repository. The remote is removed so a fetch cannot
# bring them in.
RUN git config --global user.name "Frederic van der Essen" \
    && git config --global user.email "fva@odoo.com" \
    && git config --global init.defaultBranch 20.0
WORKDIR /app
RUN git init -q . \
    && git remote add origin https://github.com/odoo/odoo.git \
    && git fetch -q --depth 50 origin c6f3b034f29220afa236737ab79d1228bdc9f3c0 \
    && git checkout -q -b 20.0-snailmail-cover-fva FETCH_HEAD \
    && git remote remove origin

# task: the fix, applied but not committed
COPY --chown=odoo change.patch /tmp/change.patch
RUN git apply /tmp/change.patch && rm /tmp/change.patch
