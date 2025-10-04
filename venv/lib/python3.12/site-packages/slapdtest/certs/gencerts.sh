#!/bin/sh
# Written by Christian Heimes
set -e

export CAOUTDIR=.
export CATMPDIR=tmp

rm -rf $CATMPDIR
rm -rf ca.pem ca.key server.pem server.key client.pem client.key
rm -rf cert9.db key4.db pkcs11.tx

mkdir -p $CAOUTDIR
mkdir -p $CATMPDIR

touch $CATMPDIR/ca.db
touch $CATMPDIR/ca.db.attr
echo '01' > $CATMPDIR/ca.crt.srl
echo '01' > $CATMPDIR/ca.crl.srl

# root CA
openssl req -new \
    -config ca.conf \
    -out $CATMPDIR/ca.csr \
    -keyout $CAOUTDIR/ca.key \
    -batch

openssl ca -selfsign \
    -config ca.conf \
    -in $CATMPDIR/ca.csr \
    -out $CAOUTDIR/ca.pem \
    -extensions ca_ext \
    -days 356300 \
    -batch

# server cert
openssl req -new \
    -config server.conf \
    -out $CATMPDIR/server.csr \
    -keyout $CAOUTDIR/server.key \
    -batch

openssl ca \
    -config ca.conf \
    -in $CATMPDIR/server.csr \
    -out $CAOUTDIR/server.pem \
    -policy match_pol \
    -extensions server_ext \
    -batch

# client cert
openssl req -new \
    -config client.conf \
    -out $CATMPDIR/client.csr \
    -keyout $CAOUTDIR/client.key \
    -batch

openssl ca \
    -config ca.conf \
    -in $CATMPDIR/client.csr \
    -out $CAOUTDIR/client.pem \
    -policy match_pol \
    -extensions client_ext \
    -batch

# cleanup
rm -rf $CATMPDIR ca.key

echo DONE
