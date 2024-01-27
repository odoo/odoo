# Use openssl to generate multiple signed RSA key/cert pairs.
#
# usage: cd path/to/dir/of/gencert.sh/; ./gencert.sh
#
# This script runs multiple openssl commands to create a fake certificate
# authority (CA) for the fake city of "Houtsiplou".
# https://fr.wiktionary.org/wiki/Houte-Si-Plou
#
# It then uses that CA to generate and sign 3 other certificates for various
# purposes: a client pair, a server pair, and an "any purpose" pair that is not
# restricted to client or server side. It also generates a self-signed pair to
# use as an "invalid" pair for testing.
#
# In Python you'll want to `load_verify_locations(cafile='path/to/ca.cert.pem')`
# to trust the certification authority and the other pairs that were signed
# with it. Note that it won't trust the autorities embedded in your OS anymore.
# https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_verify_locations
#
# This script and configuration were largely inspired by
# https://jamielinux.com/docs/openssl-certificate-authority/

set -o errexit
set -o nounset

if test ! -f openssl.conf
then
    echo Cannot find openssl.conf in the working directory.
    exit 1
fi

# reset auto generated files
rm -f *.pem index* serial*
touch index.txt
echo 1000 > serial

set -o xtrace

# create root cA
openssl genpkey -config openssl.conf -quiet -algorithm RSA -out ca.key.pem
openssl req -config openssl.conf -x509 -days 1000 \
            -extensions ca_cert -key ca.key.pem -out ca.cert.pem \
            -subj '/C=BE/L=Houtesiplou/CN=Houtesiplou Certification Authority'
openssl x509 -noout -text -in ca.cert.pem

# create any purpose
#openssl genpkey -config openssl.conf -quiet -algorithm RSA -out any_purpose.key.pem
#openssl req -config openssl.conf -new \
#            -key any_purpose.key.pem -out any_purpose.csr.pem \
#            -subj '/C=BE/L=Houtesiplou/CN=Houtesiplou Any Purpose'
#openssl ca -config openssl.conf -notext -md sha256 -batch -days 1000 -notext \
#           -extensions any_cert -keyfile ca.key.pem -cert ca.cert.pem \
#           -in any_purpose.csr.pem -out any_purpose.cert.pem
#openssl x509 -noout -text -in any_purpose.cert.pem

# create client
openssl genpkey -config openssl.conf -quiet -algorithm RSA -out client.key.pem
openssl req -config openssl.conf -new \
            -key client.key.pem -out client.csr.pem \
            -subj '/C=BE/L=Houtesiplou/CN=Houtesiplou Client'
openssl ca -config openssl.conf -notext -md sha256 -batch -days 1000 -notext \
           -extensions client_cert -keyfile ca.key.pem -cert ca.cert.pem \
           -in client.csr.pem -out client.cert.pem
openssl x509 -noout -text -in client.cert.pem

# create server
openssl genpkey -config openssl.conf -quiet -algorithm RSA -out server.key.pem
openssl req -config openssl.conf -new \
            -key server.key.pem -out server.csr.pem \
            -subj '/C=BE/L=Houtesiplou/CN=Houtesiplou Server'
openssl ca -config openssl.conf -notext -md sha256 -batch -days 1000 -notext \
           -extensions server_cert -keyfile ca.key.pem -cert ca.cert.pem \
           -in server.csr.pem -out server.cert.pem
openssl x509 -noout -text -in server.cert.pem

# create untrusted self-signed pair
openssl req -new -x509 -noenc -days 1000 -subj '/CN=SelfSigned Lmtd' \
            -out self_signed.cert.pem -keyout self_signed.key.pem

# remove useless files
rm *.csr.pem *ca.key.pem

set +o xtrace
echo -e "\nDone! Here are your files:"
find $(pwd) -name '*.*.pem'
