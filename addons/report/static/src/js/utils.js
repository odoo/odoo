odoo.define('report.utils', function (require) {
'use strict';

function get_protocol_from_url (url) {
    var a = document.createElement('a');
    a.href = url;
    return a.protocol;
}

function get_host_from_url (url) {
    var a = document.createElement('a');
    a.href = url;
    return a.host;
}

function build_origin (protocol, host) {
    return protocol + '//' + host;
}

return {
    'get_protocol_from_url': get_protocol_from_url,
    'get_host_from_url': get_host_from_url,
    'build_origin': build_origin,
};

});
