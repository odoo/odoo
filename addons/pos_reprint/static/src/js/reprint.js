openerp.pos_reprint = function(instance){
    var module   = instance.point_of_sale;
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;

    module.ProxyDevice.include({
        print_receipt: function(receipt) { 
            this._super(receipt);
            this.pos.old_receipt = receipt || this.pos.old_receipt;
        },
    });

    module.ReprintButton = module.ActionButtonWidget.extend({
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

    module.define_action_button({
        'name': 'reprint',
        'widget': module.ReprintButton,
        'condition': function(){
            return this.pos.config.iface_reprint && this.pos.config.iface_print_via_proxy;
        },
    });

};
