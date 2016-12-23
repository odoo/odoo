#!/bin/bash

ADMIN_PASSWD='admin'
method_1() {
    cat '-' << EOF
<xml>
<methodCall>
    <methodName>set_loglevel</methodName>
    <params>
        <param><value><string>$ADMIN_PASSWD</string></value>
        </param>
        <param>
        <value><string>$1</string></value>
        </param>
    </params>
</methodCall>
EOF
}
LEVEL=10

if [ -n "$1" ] ; then LEVEL=$1 ; fi

method_1 $LEVEL | POST -c 'text/xml' http://localhost:8069/xmlrpc/common
#eof
