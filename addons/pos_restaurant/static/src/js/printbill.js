function openerp_restaurant_printbill(instance,module){
    var QWeb = instance.web.qweb;
	var _t = instance.web._t;

    module.PosWidget.include({
        build_widgets: function(){
            var self = this;
            this._super();

            if(this.pos.config.iface_printbill){
                var printbill = $(QWeb.render('PrintBillButton'));

                printbill.click(function(){
                    var order = self.pos.get('selectedOrder');
                    if(order.get_orderlines().length > 0){
                        var receipt = order.export_for_printing();
                            receipt.bill = true;
                        self.pos.proxy.print_receipt(QWeb.render('BillReceipt',{
                            receipt: receipt, widget: self, pos: self.pos, order: order,
                        }));
                    }
                });

                printbill.appendTo(this.$('.control-buttons'));
                this.$('.control-buttons').removeClass('oe_hidden');
            }
        },
    });
}
