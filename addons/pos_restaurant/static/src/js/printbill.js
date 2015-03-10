odoo.define('pos_restaurant.printbill', ['point_of_sale.screens', 'web.core'], function (require) {
"use strict";

var core = require('web.core');
var screens = require('point_of_sale.screens');

var QWeb = core.qweb;

var PrintBillButton = screens.ActionButtonWidget.extend({
    template: 'PrintBillButton',
    button_click: function(){
        var order = this.pos.get('selectedOrder');
        if(order.get_orderlines().length > 0){
            var receipt = order.export_for_printing();
            receipt.bill = true;
            this.pos.proxy.print_receipt(QWeb.render('BillReceipt',{
                receipt: receipt, widget: this, pos: this.pos, order: order,
            }));
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

});
