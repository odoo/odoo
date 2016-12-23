#!/bin/bash

# ADMIN_PASSWD='admin'
method_1() {
    cat '-' << EOF
<xml>
<methodCall>
    <methodName>list_http_services</methodName>
    <params>
    </params>
</methodCall>
EOF
}

method_1 | POST -c 'text/xml' http://localhost:8069/xmlrpc/common
#eof
