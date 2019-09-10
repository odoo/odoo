openerp.pos_discount = function(instance){
    var module   = instance.point_of_sale;
    var round_pr = instance.web.round_precision
    var QWeb = instance.web.qweb;

    QWeb.add_template('/pos_discount/static/src/xml/discount.xml');

    module.PosWidget.include({
        build_widgets: function(){
            var self = this;
            this._super();
            
            if(!this.pos.config.discount_product_id){
                return;
            }

            var discount = $(QWeb.render('DiscountButton'));

            discount.click(function(){
                var order    = self.pos.get('selectedOrder');
                var product  = self.pos.db.get_product_by_id(self.pos.config.discount_product_id[0]);
                var discount = - self.pos.config.discount_pc/ 100.0 * order.getTotalTaxIncluded();
                if( discount < 0 ){
                    order.addProduct(product, { price: discount });
                }
            });

            discount.appendTo(this.$('.control-buttons'));
            this.$('.control-buttons').removeClass('oe_hidden');
        },
    });

};

