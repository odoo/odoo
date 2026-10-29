# The environment every eval task starts from: runbot's 20.0 image (odoo/runbot,
# "Docker Master Noble" on ubuntu:resolute), plus what Harbor and the tasks need.
# Built once, tagged odoo-evals:20.0; each task's Dockerfile adds its checkout:
#
#     docker build -t odoo-evals:20.0 skills/evals/docker
#
# Runbot's layers are kept in order. Its amd64-only downloads (chrome,
# paper-muncher) are skipped on arm64 hosts; wkhtmltopdf and odoo-ls are fetched
# for the host architecture. Files runbot caches are fetched with ADD, from 20.0.
FROM ubuntu:resolute
ARG PG_VERSION=18
ARG ODOO_BRANCH=20.0
ARG TARGETARCH

ENV LANG=C.UTF-8
USER root

# runbot: base debian packages
RUN set -x ; \
    apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends apt-transport-https build-essential ca-certificates curl faketime file fonts-freefont-ttf fonts-noto-cjk gawk gnupg gsfonts libldap2-dev libjpeg9-dev libsasl2-dev libxslt1-dev lsb-release npm ocrmypdf sed sudo unzip xfonts-75dpi zip zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# runbot: postgresql server
ENV PG_VERSION=${PG_VERSION}
RUN set -x ; \
    apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends postgresql-${PG_VERSION} postgresql-${PG_VERSION}-pgvector locales \
    && rm -rf /var/lib/apt/lists/*
RUN locale-gen en_US.UTF-8

# runbot: python debian packages
RUN set -x ; \
    apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends publicsuffix python3 flake8 python3-dbfread python3-dev python3-gevent python3-pip python3-setuptools python3-wheel python3-markdown python3-mock python3-phonenumbers python3-websocket python3-google-auth libpq-dev pylint python3-jwt python3-asn1crypto python3-html2text python3-suds python3-xmlsec python3-markdown2 python3-aiosmtpd python3-paramiko \
    && rm -rf /var/lib/apt/lists/*

# runbot: wkhtmltopdf 0.12.6.1-2 (jammy build), for the host architecture
RUN curl -sSL https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_${TARGETARCH}.deb -o /tmp/wkhtml.deb \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get -y install --no-install-recommends --fix-missing -qq /tmp/wkhtml.deb \
    && rm -rf /var/lib/apt/lists/* \
    && rm /tmp/wkhtml.deb

# runbot: npm lint tools
ENV NODE_PATH=/usr/lib/node_modules/
ENV npm_config_prefix=/usr
RUN npm install --force -g rtlcss@3.4.0 es-check@6.0.0 eslint@8.1.0 prettier@2.7.1 eslint-config-prettier@8.5.0 eslint-plugin-prettier@4.2.1

# runbot: the branch's debian/control dependencies, with the latest postgresql-client
ADD https://raw.githubusercontent.com/odoo/odoo/${ODOO_BRANCH}/debian/control /tmp/control.txt
RUN curl -sSL https://www.postgresql.org/media/keys/ACCC4CF8.asc -o /etc/apt/trusted.gpg.d/psql_client.asc \
    && echo "deb http://apt.postgresql.org/pub/repos/apt/ `lsb_release -s -c`-pgdg main" > /etc/apt/sources.list.d/pgclient.list \
    && apt-get update \
    && sed -n '/^Depends:/,/^[A-Z]/p' /tmp/control.txt \
        | awk '/^ [a-z]/ { gsub(/,/,"") ; gsub(" ", "") ; print $NF }' | sort -u \
        | DEBIAN_FRONTEND=noninteractive xargs apt-get install -y -qq --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# runbot: chrome 150.0.7871.114-1 (amd64 only)
RUN if [ "$TARGETARCH" = amd64 ]; then \
        curl -sSL https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_150.0.7871.114-1_amd64.deb -o /tmp/chrome.deb \
        && apt-get update \
        && apt-get -y install --no-install-recommends /tmp/chrome.deb \
        && rm /tmp/chrome.deb \
        && rm -rf /var/lib/apt/lists/* ; \
    fi

# runbot: Odoo's phonenumbers package
ADD https://packages.odoo.com/pub/python3-phonenumbers_8.12.57-5+odoo2_all.deb /phonenumbers.deb
RUN set -x ; \
    apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends /phonenumbers.deb \
    && rm -rf /var/lib/apt/lists/*

# runbot: GeoIP test databases
ADD https://github.com/maxmind/MaxMind-DB/raw/main/test-data/GeoIP2-City-Test.mmdb /usr/share/GeoIP/GeoLite2-City.mmdb
ADD https://github.com/maxmind/MaxMind-DB/raw/main/test-data/GeoIP2-Country-Test.mmdb /usr/share/GeoIP/GeoLite2-Country.mmdb

# runbot: virtualenv on top of the system packages
RUN set -x ; \
    apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3-venv \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /venv/main --system-site-packages
ENV PATH="/venv/main/bin:$PATH"

# runbot: pip packages and the branch's requirements.txt
RUN python3 -m pip install --no-cache-dir pdf417gen==0.7.1 pylint==4.0.3 unidiff==0.7.3 semgrep==1.116.0 ruff==0.16.1 coverage==7.4.4
ADD https://raw.githubusercontent.com/odoo/odoo/${ODOO_BRANCH}/requirements.txt /tmp/requirements.txt
# libsass 0.22.0 has no linux arm64 wheel and its sdist does not build on Python
# 3.14: on arm64, take Ubuntu's python3-libsass (0.23) through the system site.
RUN if [ "$TARGETARCH" = arm64 ]; then \
        apt-get update \
        && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3-libsass \
        && rm -rf /var/lib/apt/lists/* \
        && sed -i '/^libsass==/d' /tmp/requirements.txt ; \
    fi \
    && python3 -m pip install --no-cache-dir -r /tmp/requirements.txt

# runbot: user and virtualenv permissions
RUN groupadd -g 10000 odoo && useradd --create-home -u 10000 -g odoo -G audio,video odoo
RUN chmod 777 -R /venv/main

ENV PYTHONHASHSEED=0
ENV ODOO_RUNBOT=1

# runbot: libfaketime at a fixed commit
RUN set -x ; \
    dpkg-query -l faketime && DEBIAN_FRONTEND=noninteractive apt-get purge -y --no-install-recommends faketime libfaketime || true \
    && curl -sSL https://github.com/wolfcw/libfaketime/archive/3062fb20041552727bdb810456d2f1b4001b341f.tar.gz -o /tmp/faketime-sources.tar.gz \
    && cd /tmp \
    && tar xvf faketime-sources.tar.gz \
    && cd libfaketime-3062fb20041552727bdb810456d2f1b4001b341f \
    && make \
    && make install \
    && rm /tmp/faketime-sources.tar.gz \
    && rm -rf /tmp/libfaketime-3062fb20041552727bdb810456d2f1b4001b341f

# runbot: paper-muncher 0.9.0 (amd64 only)
RUN if [ "$TARGETARCH" = amd64 ]; then \
        curl -sSL https://github.com/odoo/paper-muncher/releases/download/v0.9.0/paper-muncher_v0.9.0_resolute_amd64.deb -o /tmp/paper.deb \
        && apt-get update \
        && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends /tmp/paper.deb \
        && rm /tmp/paper.deb \
        && rm -rf /var/lib/apt/lists/* ; \
    fi
ENV PATH="$PATH:/opt/paper-muncher/bin"

# runbot: odoo-ls 1.6.0 and typeshed, for the host architecture
ADD https://github.com/python/typeshed/archive/refs/heads/main.zip /tmp/typeshed.zip
RUN mkdir /usr/local/bin/typeshed && unzip -q /tmp/typeshed.zip -d /tmp/typeshed && mv /tmp/typeshed/typeshed-main/* /usr/local/bin/typeshed && chmod 775 -R /usr/local/bin/typeshed \
    && rm -rf /tmp/typeshed /tmp/typeshed.zip
RUN arch=$([ "$TARGETARCH" = arm64 ] && echo aarch64 || echo x86_64) \
    && curl -sSL https://github.com/odoo/odoo-ls/releases/download/1.6.0/odoo-linux-${arch}-1.6.0.tar.gz -o /tmp/odools.tar.gz \
    && cd /usr/local/bin && tar xfz /tmp/odools.tar.gz && chmod 775 /usr/local/bin/odoo_ls_server && rm /tmp/odools.tar.gz

# evals: runbot's lint tools are installed; clear its npm prefix, which nvm (the
# codex installer) refuses to run with
ENV npm_config_prefix=

# evals: git for the agent, ripgrep for the codex installer, uv for the verifier (rewardkit)
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends git ripgrep \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
RUN mkdir /app && chown odoo:odoo /app

# evals: a PostgreSQL cluster owned by odoo, so the agent can run Odoo and its
# tests; the entrypoint starts it with the container
RUN chown odoo:odoo /var/run/postgresql
COPY start-postgres.sh /usr/local/bin/start-postgres

# evals: the developer the agent commits as
USER odoo
ENV PGDATA=/home/odoo/pgdata
ENV PATH="$PATH:/usr/lib/postgresql/${PG_VERSION}/bin"
RUN initdb -D "$PGDATA" -U odoo --auth=trust --encoding=UTF8 --locale=C.UTF-8 > /dev/null
RUN git config --global user.name "John Doe" \
    && git config --global user.email "jdoe@odoo.com" \
    && git config --global init.defaultBranch 20.0

# evals: checkouts leave out the repository's skills/ folder, so an agent run
# without skills cannot read them from the tree; the runs that attach skills
# get them from the job. Every repository the tasks create inherits it.
RUN mkdir -p ~/.git-template/info \
    && printf '/*\n!/skills/\n' > ~/.git-template/info/sparse-checkout \
    && git config --global init.templateDir ~/.git-template \
    && git config --global core.sparseCheckout true
WORKDIR /app
ENTRYPOINT ["/usr/local/bin/start-postgres"]
CMD ["bash"]
