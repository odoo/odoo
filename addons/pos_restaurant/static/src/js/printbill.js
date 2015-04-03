openerp.pos_restaurant.load_printbill = function(instance,module){
    var QWeb = instance.web.qweb;
	var _t = instance.web._t;

    module.BillScreenWidget = module.ReceiptScreenWidget.extend({
        template: 'BillScreenWidget',
        click_next: function(){
            this.gui.show_screen('products');
        },
        click_back: function(){
            this.gui.show_screen('products');
        },
        render_receipt: function(){
            this._super();
            this.$('.receipt-paymentlines').remove();
            this.$('.receipt-change').remove();
        },
        print_web: function(){
            window.print();
        },
    });

    module.Gui.define_screen({name:'bill', widget:module.BillScreenWidget});
    
    module.PrintBillButton = module.ActionButtonWidget.extend({
        template: 'PrintBillButton',
        print_xml: function(){
            var order = this.pos.get('selectedOrder');
            if(order.get_orderlines().length > 0){
                var receipt = order.export_for_printing();
                receipt.bill = true;
                this.pos.proxy.print_receipt(QWeb.render('BillReceipt',{
                    receipt: receipt, widget: this, pos: this.pos, order: order,
                }));
            }
        },
        button_click: function(){
            if (!this.pos.config.iface_print_via_proxy) {
                this.gui.show_screen('bill');
            } else {
                this.print_xml();
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

