openerp.pos_reprint = function(instance){
    var module   = instance.point_of_sale;
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;

    QWeb.add_template('/pos_reprint/static/src/xml/reprint.xml');

    module.PosWidget.include({
        build_widgets: function(){
            var self = this;
            this._super();
            this.pos.old_receipt = null;

            if(!this.pos.config.reprint) return;

            var reprint = $(QWeb.render('ReprintButton'));

            reprint.click(function(){
                if(self.pos.old_receipt) {
                    self.pos.proxy.print_receipt(self.pos.old_receipt);
                }
                else {
                    self.pos_widget.screen_selector.show_popup("error", {
                        message: _t("Nothing to Print"),
                        comment: _t("There is no previous receipt to print."),
                    });
                }
            });

            reprint.appendTo(this.$('.control-buttons'));
            this.$('.control-buttons').removeClass('oe_hidden');
        },
    });

    module.ProxyDevice.include({
        print_receipt: function(receipt) {
            this.pos.old_receipt = receipt || this.pos.old_receipt;
            this._super(receipt);
        }
    });

};