openerp.pos_restaurant.load_printbill = function(instance,module){
    var QWeb = instance.web.qweb;
	var _t = instance.web._t;

    module.PrintBillButton = module.ActionButtonWidget.extend({
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

    module.define_action_button({
        'name': 'print_bill',
        'widget': module.PrintBillButton,
        'condition': function(){ 
            return this.pos.config.iface_printbill;
        },
    });
};

