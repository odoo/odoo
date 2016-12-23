#!/bin/bash

# ADMIN_PASSWD='admin'
method_1() {
    cat '-' << EOF
<xml>
<methodCall>
    <methodName>get_stats</methodName>
    <params>
    </params>
</methodCall>
EOF
}
LEVEL=10

if [ -n "$1" ] ; then LEVEL=$1 ; fi

method_1 $LEVEL | POST -c 'text/xml' http://localhost:8069/xmlrpc/common
#eof
