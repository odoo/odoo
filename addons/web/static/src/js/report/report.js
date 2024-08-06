odoo.define('report', function (require) {
'use strict';

require('web.dom_ready');
var utils = require('report.utils');

if (window.self === window.top) {
    return;
}

$(document.body)
    .addClass('o_in_iframe')
    .addClass('container-fluid')
    .removeClass('container');

var web_base_url = window.origin;
var trusted_host = utils.get_host_from_url(web_base_url);
var trusted_protocol = utils.get_protocol_from_url(web_base_url);
var trusted_origin = utils.build_origin(trusted_protocol, trusted_host);

// Allow sending commands to the webclient
// `do_action` command
$('[res-id][res-model][view-type]')
    .wrap('<a/>')
    .attr('href', '#')
    .on('click', function (ev) {
        ev.preventDefault();
        var action = {
            'type': 'ir.actions.act_window',
            'view_mode': $(this).attr('view-mode') || $(this).attr('view-type'),
            'res_id': Number($(this).attr('res-id')),
            'res_model': $(this).attr('res-model'),
            'views': [
                [$(this).attr('view-id') || false, $(this).attr('view-type')],
            ],
        };
        window.parent.postMessage({
            'message': 'report:do_action',
            'action': action,
        }, trusted_origin);
    });
});
