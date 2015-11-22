#!/usr/bin/env bash
# apt-get install p7zip-full
set -e

mkdir -p wkhtmltopdf less
TEMPDIR=`mktemp -d -t odoo_windows_build_XXXX`
function cleanup {
  rm -rf $TEMPDIR
}
trap cleanup EXIT

# postgresql
wget -q http://get.enterprisedb.com/postgresql/postgresql-9.3.5-1-windows.exe

# wkhtmltopdf
wget -q -P $TEMPDIR http://download.gna.org/wkhtmltopdf/0.12/0.12.1/wkhtmltox-0.12.1.2_msvc2013-win32.exe
7z x -o$TEMPDIR $TEMPDIR/wkhtmltox-0.12.1.2_msvc2013-win32.exe
cp $TEMPDIR/bin/wkhtmltopdf.exe ./wkhtmltopdf

# less
pushd less
wget -q https://github.com/duncansmart/less.js-windows/releases/download/v2.5.1/less.js-windows-v2.5.1a.zip
unzip less.js-windows-v2.5.1a.zip
rm less.js-windows-v2.5.1a.zip

