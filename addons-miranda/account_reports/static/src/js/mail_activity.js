odoo.define('account_reports.activity', function (require) {
"use strict";

var core = require('web.core');
var AccountActivity = require('account.activity');

var _t = core._t;

AccountActivity.include({
    events: _.extend({
        'click .o_open_vat_report': '_onOpenReport',
    }, AccountActivity.prototype.events),

     _onOpenReport: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var self = this;
        var id = $(e.target).data('id') || false;
        if (id) {
            this._rpc({
                    model: 'mail.activity',
                    method: 'action_open_tax_report',
                    args: [id],
                }).then(function (action) {
                    self.do_action(action);
                });
        }
    }
});

});
