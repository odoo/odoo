# Ubuntu 22.04
FROM ubuntu:jammy-20260509

# variables & locales
ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qq \
    && apt-get install -y locales -qq \
    && locale-gen en_US.UTF-8 \
    && dpkg-reconfigure locales \
    && /usr/sbin/update-locale LANG=en_US.UTF-8 \
    # dependencies for odoo or python packages
    && apt-get install -y --no-install-recommends libjpeg-dev libsasl2-dev libxslt-dev libxml2-dev ca-certificates tzdata \
    curl file xfonts-75dpi xfonts-base unzip build-essential fontconfig libfontconfig1 libpng16-16 \
    libldap2-dev libssl-dev poppler-utils fonts-dejavu cabextract libfreetype6 git libffi-dev libc6 \
    libstdc++6 libpoppler-cpp-dev pkg-config librdkafka-dev libpq-dev \
    libbz2-dev libreadline-dev libsqlite3-dev liblzma-dev zlib1g-dev libdmtx0b \
    && rm -rf /var/lib/apt/lists/*
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

ARG TARGETARCH

# wkhtmltopdf
RUN WKHTMLTOPDF_VERSION=0.12.6.1-2 \
    && if [ "$TARGETARCH" = "arm64" ]; then \
        WKHTMLTOPDF_ARCH="arm64"; \
        WKHTMLTOPDF_SHA1="0edcc573e8bbd7ba12885671e75cee8efe3ae11d"; \
    else \
        WKHTMLTOPDF_ARCH="amd64"; \
        WKHTMLTOPDF_SHA1="800eb1c699d07238fee77bf9df1556964f00ffcf"; \
    fi \
    && curl -sL -o /tmp/wkhtmltox.deb https://github.com/wkhtmltopdf/packaging/releases/download/${WKHTMLTOPDF_VERSION}/wkhtmltox_${WKHTMLTOPDF_VERSION}.jammy_${WKHTMLTOPDF_ARCH}.deb \
    && echo "${WKHTMLTOPDF_SHA1} /tmp/wkhtmltox.deb" | sha1sum -c - \
    && apt-get install -y --no-install-recommends /tmp/wkhtmltox.deb \
    && rm -rf /tmp/wkhtmltox.deb

# Node.js
ENV PATH="${PATH}:/opt/node/bin"
RUN NODE_VERSION=20.20.2 \
    && if [ "$TARGETARCH" = "arm64" ]; then \
        NODE_ARCH="arm64"; \
        NODE_SHA256="73093db209e4e9e09dd7d15a47aeaab1b74833830df03efa5f942a1122c5fa71"; \
    else \
        NODE_ARCH="x64"; \
        NODE_SHA256="df770b2a6f130ed8627c9782c988fda9669fa23898329a61a871e32f965e007d"; \
    fi \
    && curl -sL -o /tmp/node.tar.xz https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-$NODE_ARCH.tar.xz \
    && echo "$NODE_SHA256 /tmp/node.tar.xz" | sha256sum -c - \
    && tar -xf /tmp/node.tar.xz \
    && mv node-v$NODE_VERSION-linux-$NODE_ARCH /opt/node \
    && rm -rf /tmp/node.tar.xz

# lessc
RUN npm install -g less@4.6.4

# odoo directories
RUN useradd -s /usr/sbin/nologin --create-home --password odoo odoo \
  && mkdir /home/odoo/.local \
  && chown odoo:odoo /home/odoo/.local \
  && mkdir --parents /opt/odoo/tests \
  && chown --recursive odoo:odoo /opt/odoo

# Python
ENV PYENV_ROOT="/.pyenv"
ENV PATH="${PYENV_ROOT}/shims:${PYENV_ROOT}/bin:${PATH}"
COPY .python-version .
RUN PYTHON_VERSION="$(cat .python-version)" \
    && git clone --depth 1 -b v2.6.31 https://github.com/pyenv/pyenv.git "${PYENV_ROOT}" \
    && pyenv install --verbose ${PYTHON_VERSION} \
    && pyenv global ${PYTHON_VERSION} \
    && rm .python-version

# Poetry
RUN pip install --no-cache-dir poetry==2.4.1

USER odoo
WORKDIR /opt/odoo

# Dependencies
ENV VIRTUAL_ENV="/opt/odoo/.venv"
ENV VIRTUAL_ENV_PROMPT="odoo"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
ARG VIRTUALENV_PIP=26.0.1
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.in-project true && \
    poetry install --no-root --no-interaction && \
    rm -rf ~/.cache/pypoetry

COPY --chown=odoo:odoo . .

EXPOSE 8069 8072
VOLUME ["/home/odoo/.local"]
