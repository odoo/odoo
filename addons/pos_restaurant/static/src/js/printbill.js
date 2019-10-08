odoo.define('pos_restaurant.printbill', function (require) {
"use strict";

var core = require('web.core');
var screens = require('point_of_sale.screens');
var gui = require('point_of_sale.gui');

var QWeb = core.qweb;

var BillScreenWidget = screens.ReceiptScreenWidget.extend({
    template: 'BillScreenWidget',
    click_next: function(){
        this.gui.show_screen('products');
    },
    click_back: function(){
        this.gui.show_screen('products');
    },
    get_receipt_render_env: function(){
        var render_env = this._super();
        render_env.receipt.bill = true;
        return render_env;
    },
    render_receipt: function(){
        this._super();
        this.$('.receipt-change').remove();
    },
});

gui.define_screen({name:'bill', widget: BillScreenWidget});

var PrintBillButton = screens.ActionButtonWidget.extend({
    template: 'PrintBillButton',
    button_click: function(){
        var order = this.pos.get('selectedOrder');
        if(order.get_orderlines().length > 0) {
            this.gui.show_screen('bill');
        } else {
          this.gui.show_popup('error', {
              'title': _t('Nothing to Print'),
              'body':  _t('There are no order lines'),
          });
        }
    },
});

screens.define_action_button({
    'name': 'print_bill',
    'widget': PrintBillButton,
    'condition': function(){
        return this.pos.config.iface_printbill;
    },
});
return {
    BillScreenWidget: BillScreenWidget,
    PrintBillButton: PrintBillButton,
};
});
