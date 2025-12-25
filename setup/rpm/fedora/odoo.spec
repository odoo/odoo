%global __requires_exclude ^.*odoo/addons/mail/static/scripts/odoo-mailgate.py$

%global forgeurl https://github.com/NorTK/odoo
Version: 19.0.0
%forgemeta

Name: odoo
Summary: NorTK Odoo Server
Release: 1%{?dist}
URL: %{forgeurl}
Source0: %{forgesource}
License: LGPL-3
Group: Development/Libraries
BuildArch: noarch

Requires: sassc
Requires: libsass
Requires: postgresql
Requires: postgresql-contrib
Requires: postgresql-devel
Requires: postgresql-libs
Requires: postgresql-server
Requires: python3-PyPDF2
Requires: python3-asn1crypto
Requires: python3-babel
Requires: python3-cbor2
Requires: python3-chardet
Requires: python3-cryptography
Requires: python3-dateutil
Requires: python3-devel
Requires: python3-docutils
Requires: python3-freezegun
Requires: python3-geoip2
Requires: python3-gevent
Requires: python3-greenlet
Requires: python3-idna
Requires: python3-jinja2
Requires: python3-libsass
Requires: python3-lxml
Requires: python3-lxml-html-clean
Requires: python3-magic
Requires: python3-markupsafe
Requires: python3-mock
Requires: python3-num2words
Requires: python3-ofxparse
Requires: python3-openpyxl
Requires: python3-passlib
Requires: python3-pillow
Requires: python3-polib
Requires: python3-psutil
Requires: python3-psycopg2
Requires: python3-pyldap
Requires: python3-pyOpenSSL
Requires: python3-pyserial
Requires: python3-pytz
Requires: python3-pyusb
Requires: python3-qrcode
Requires: python3-reportlab
Requires: python3-requests
Requires: python3-rjsmin
Requires: python3-six
Requires: python3-stdnum
Requires: python3-vobject
Requires: python3-werkzeug
Requires: python3-wheel
Requires: python3-xlrd
Requires: python3-xlsxwriter
Requires: python3-xlwt
Requires: python3-zeep

BuildRequires: python3-devel
BuildRequires: pyproject-rpm-macros
BuildRequires: python3-asn1crypto
BuildRequires: python3-packaging
BuildRequires: python3-pip
BuildRequires: python3-setuptools
BuildRequires: python3-cbor2
BuildRequires: python3-geoip2
BuildRequires: python3-gevent
BuildRequires: python3-libsass
BuildRequires: python3-lxml-html-clean
BuildRequires: python3-num2words
BuildRequires: python3-ofxparse
BuildRequires: python3-passlib
BuildRequires: python3-PyPDF2
BuildRequires: python3-stdnum
BuildRequires: python3-pyusb
BuildRequires: python3-qrcode
BuildRequires: python3-rjsmin
BuildRequires: python3-vobject
BuildRequires: python3-xlwt
BuildRequires: python3-zeep

%description
Odoo is a complete ERP and CRM. The main features are accounting (analytic
and financial), stock management, sales and purchases management, tasks
automation, marketing campaigns, help desk, POS, etc. Technical features include
a distributed server, an object database, a dynamic GUI,
customizable reports, and XML-RPC interfaces.

%generate_buildrequires
%pyproject_buildrequires

%prep
%forgesetup

%build
%pyproject_wheel

%install
%pyproject_install

%post
#!/usr/bin/bash

set -e

ODOO_CONFIGURATION_DIR=/etc/odoo
ODOO_CONFIGURATION_FILE=$ODOO_CONFIGURATION_DIR/odoo.conf
ODOO_DATA_DIR=/var/lib/odoo
ODOO_GROUP="odoo"
ODOO_LOG_DIR=/var/log/odoo
ODOO_LOG_FILE=$ODOO_LOG_DIR/odoo-server.log
ODOO_USER="odoo"

if ! getent passwd | grep -q "^odoo:"; then
    groupadd $ODOO_GROUP
    adduser --system --no-create-home $ODOO_USER -g $ODOO_GROUP
fi
# Register "$ODOO_USER" as a postgres user with "Create DB" role attribute
su - postgres -c "createuser -d -R -S $ODOO_USER" 2> /dev/null || true
# Configuration file
mkdir -p $ODOO_CONFIGURATION_DIR
# can't copy debian config-file as addons_path is not the same
if [ ! -f $ODOO_CONFIGURATION_FILE ]
then
    echo "[options]
; This is the password that allows database operations:
; admin_passwd = admin
db_host = False
db_port = False
db_user = $ODOO_USER
db_password = False
addons_path = %{python3_sitelib}/odoo/addons
default_productivity_apps = True
" > $ODOO_CONFIGURATION_FILE
    chown $ODOO_USER:$ODOO_GROUP $ODOO_CONFIGURATION_FILE
    chmod 0640 $ODOO_CONFIGURATION_FILE
fi
# Log
mkdir -p $ODOO_LOG_DIR
chown $ODOO_USER:$ODOO_GROUP $ODOO_LOG_DIR
chmod 0750 $ODOO_LOG_DIR
# Data dir
mkdir -p $ODOO_DATA_DIR
chown $ODOO_USER:$ODOO_GROUP $ODOO_DATA_DIR

INIT_FILE=/lib/systemd/system/odoo.service
touch $INIT_FILE
chmod 0700 $INIT_FILE
cat << EOF > $INIT_FILE
[Unit]
Description=Odoo Open Source ERP and CRM
After=network.target

[Service]
Type=simple
User=odoo
Group=odoo
ExecStart=/usr/bin/odoo --config $ODOO_CONFIGURATION_FILE --logfile $ODOO_LOG_FILE
KillMode=mixed

[Install]
WantedBy=multi-user.target
EOF

%files
%{_bindir}/odoo
%{python3_sitelib}/%{name}-*.dist-info
%{python3_sitelib}/addons
%{python3_sitelib}/utils
%{python3_sitelib}/%{name}
%pycached %exclude %{python3_sitelib}/doc/cla/stats.py
%pycached %exclude %{python3_sitelib}/setup/*.py
%exclude %{python3_sitelib}/setup/odoo

%changelog
* Wed Dec 10 2025 Rénich Bon Ćirić <renich@evalinux.com> - 19.0.0-1
- Made the SPEC standard format.
- Implemented SCM support.
