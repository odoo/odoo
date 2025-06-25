#!/bin/sh
# Written by Christian Heimes
set -e

CATMPDIR=tmp
PASSFILE=${CATMPDIR}/passwd.txt
NSSDB=sql:${CAOUTDIR}

mkdir -p $CATMPDIR

# Create PKCS#12 files for NSSDB import
echo "dummy" > $PASSFILE
openssl pkcs12 -name "servercert" -in server.pem -inkey server.key \
    -caname "testca" -CAfile ca.pem \
    -password "file:${PASSFILE}" -export -out server.p12
openssl pkcs12 -name "clientcert" -in client.pem -inkey client.key \
    -caname "testca" -CAfile ca.pem \
    -password "file:${PASSFILE}" -export -out client.p12

# Create NSS DB
certutil -d $NSSDB -N --empty-password
certutil -d $NSSDB -A -n "testca" -t CT,, -a -i ca.pem
pk12util -d $NSSDB -i server.p12 -w ${PASSFILE}
pk12util -d $NSSDB -i client.p12 -w ${PASSFILE}
certutil -d $NSSDB -L

# cleanup
rm -rf $CATMPDIR server.p12 client.p12