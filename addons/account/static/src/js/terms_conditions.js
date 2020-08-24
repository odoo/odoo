/* eslint-disable no-undef */
odoo.define('account.terms_conditions', function (require) {
    "use strict";
    const publicWidget = require('web.public.widget');
    publicWidget.registry.TermsConditonsView = publicWidget.Widget.extend({
        selector: '#terms_conditions',
        events: {
            'click': '_openSettings'
        },
        _openSettings: function (ev) {
            console.log("plop is called");
            return this.do_action({
                res_model: 'res.config.settings',
                name: 'Settings',
                type: 'ir.actions.act_window',
                views: [[false, 'form']],
                target: 'new',
                context: {'module': 'general_settings'},
            });
        }
    });

    // Add client actions
    return publicWidget.registry.TermsConditonsView;
});
