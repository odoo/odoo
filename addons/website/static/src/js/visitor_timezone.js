//
// This file is meant to determine the timezone of a website visitor
// If the visitor already exists, no need to keep the timezone cookie
// as the timezone is set on the visitor.
//
odoo.define('website.visitor_timezone', function (require) {
'use strict';

var ajax = require('web.ajax');
var utils = require('web.utils');
var publicWidget = require('web.public.widget');

publicWidget.registry.visitorTimezone = publicWidget.Widget.extend({
    selector: '#wrapwrap',

    start: function () {
        if (!localStorage.getItem('website.found_visitor_timezone')) {
            var timezone = jstz.determine().name();
            this._rpc({
                route: '/website/update_visitor_timezone',
                params: {
                    'timezone': timezone,
                },
            }).then(function (result) {
                if (result) {
                    localStorage.setItem('website.found_visitor_timezone', true);
                }
            });
        }
        return this._super.apply(this, arguments);
    },
});

return publicWidget.registry.visitorTimezone;

});
