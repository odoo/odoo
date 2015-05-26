#!/usr/bin/env bash
# apt-get install p7zip-full
set -e

mkdir -p wkhtmltopdf less/node_modules
TEMPDIR=`mktemp -d -t odoo_windows_build_XXXX`
function cleanup {
  rm -rf $TEMPDIR
}
trap cleanup EXIT

# postgresql
wget -q http://get.enterprisedb.com/postgresql/postgresql-9.3.5-1-windows.exe

# wkhtmltopdf
wget -q -P $TEMPDIR http://downloads.sourceforge.net/project/wkhtmltopdf/0.12.1/wkhtmltox-0.12.1.2_msvc2013-win32.exe
7z x -o$TEMPDIR $TEMPDIR/wkhtmltox-0.12.1.2_msvc2013-win32.exe
cp $TEMPDIR/bin/wkhtmltopdf.exe ./wkhtmltopdf

# less
wget -q -P ./less http://nodejs.org/dist/latest/node.exe
echo '"%~dp0\node.exe" "%~dp0\.\node_modules\less.js\bin\lessc" %*' > ./less/lessc.cmd
pushd ./less/node_modules
wget -q https://github.com/less/less.js/archive/v2.0.0.tar.gz -O - | tar xz && mv less.js-2.0.0 less.js
wget -q https://github.com/then/promise/archive/6.0.1.tar.gz -O - | tar xz && mv promise-6.0.1 promise
wget -q https://github.com/kriskowal/asap/archive/v2.0.0.tar.gz -O - | tar xz && mv asap-2.0.0 asap
wget -q -P $TEMPDIR https://github.com/less/less-plugin-clean-css/archive/clean-css-3.zip
unzip $TEMPDIR/clean-css-3.zip && mv less-plugin-clean-css-clean-css-3 less-plugin-clean-css-clean-css
