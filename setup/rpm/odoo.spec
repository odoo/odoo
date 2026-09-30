%global name odoo
%global unmangled_version %{version}
%global __requires_exclude ^.*odoo/addons/mail/static/scripts/odoo-mailgate.py$

Summary: Odoo Server
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: LGPL-3
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Odoo S.A. <info@odoo.com>
Requires: sassc
BuildRequires: python3-devel
BuildRequires: pyproject-rpm-macros
Url: https://www.odoo.com

%description
Odoo is a complete ERP and CRM. The main features are accounting (analytic
and financial), stock management, sales and purchases management, tasks
automation, marketing campaigns, help desk, POS, etc. Technical features include
a distributed server, an object database, a dynamic GUI,
customizable reports, and XML-RPC interfaces.

%generate_buildrequires
%pyproject_buildrequires

%prep
%autosetup

%build
%py3_build

%install
%py3_install

%post
#!/bin/sh

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
%{python3_sitelib}/%{name}-*.egg-info
%{python3_sitelib}/%{name}
%pycached %exclude %{python3_sitelib}/doc/cla/stats.py
%pycached %exclude %{python3_sitelib}/setup/*.py
%exclude %{python3_sitelib}/setup/odoo

%changelog
* %{build_date} Christophe Monniez <moc@odoo.com> - %{version}-%{release}
- Latest updates
