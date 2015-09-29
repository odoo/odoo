odoo.define('pos_reprint.pos_reprint', function (require) {
"use strict";

var devices = require('point_of_sale.devices');
var screens = require('point_of_sale.screens');
var core = require('web.core');

var _t = core._t;

devices.ProxyDevice.include({
    print_receipt: function(receipt) { 
        this._super(receipt);
        this.pos.old_receipt = receipt || this.pos.old_receipt;
    },
});

var ReprintButton = screens.ActionButtonWidget.extend({
    template: 'ReprintButton',
    button_click: function() {
        if (this.pos.old_receipt) {
            this.pos.proxy.print_receipt(this.pos.old_receipt);
        } else {
            this.gui.show_popup('error', {
                'title': _t('Nothing to Print'),
                'body':  _t('There is no previous receipt to print.'),
            });
        }
    },
});

screens.define_action_button({
    'name': 'reprint',
    'widget': ReprintButton,
    'condition': function(){
        return this.pos.config.iface_reprint && this.pos.config.iface_print_via_proxy;
    },
});

});
