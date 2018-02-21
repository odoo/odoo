odoo.define('pos_reprint.pos_reprint', function (require) {
"use strict";

var screens = require('point_of_sale.screens');
var gui = require('point_of_sale.gui');
var core = require('web.core');

var _t = core._t;

screens.ReceiptScreenWidget.include({
    get_receipt_render_env: function() {
        this.pos.last_receipt_render_env = this._super();
        return this.pos.last_receipt_render_env;
    }
});

var ReprintReceiptScreenWidget = screens.ReceiptScreenWidget.extend({
    template: 'ReprintReceiptScreenWidget',
    render_change: function() {},
    click_next: function() {},
    click_back: function() {
        this._super();
        this.gui.show_screen('products');
    },
    get_receipt_render_env: function() {
        return this.pos.last_receipt_render_env;
    },
});
gui.define_screen({name:'reprint_receipt', widget: ReprintReceiptScreenWidget});

var ReprintButton = screens.ActionButtonWidget.extend({
    template: 'ReprintButton',
    button_click: function() {
        if (this.pos.last_receipt_render_env) {
            this.gui.show_screen('reprint_receipt');
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
        return this.pos.config.iface_print_via_proxy;
    },
});

return {
    ReprintReceiptScreenWidget: ReprintReceiptScreenWidget,
};

});
