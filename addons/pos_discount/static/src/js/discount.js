openerp.pos_discount = function(instance){
    var module   = instance.point_of_sale;
    var round_pr = instance.web.round_precision
    var QWeb = instance.web.qweb;

    QWeb.add_template('/pos_discount/static/src/xml/discount.xml');

    module.DiscountButton = module.ActionButtonWidget.extend({
        template: 'DiscountButton',
        button_click: function(){
            var order    = this.pos.get_order();
            var product  = this.pos.db.get_product_by_id(this.pos.config.discount_product_id[0]);
            var discount = - this.pos.config.discount_pc/ 100.0 * order.get_total_with_tax();
            if( discount < 0 ){
                order.add_product(product, { price: discount });
            }
        },
    });

    module.define_action_button({
        'name': 'discount',
        'widget': module.DiscountButton,
        'condition': function(){
            return this.pos.config.discount_product_id;
        },
    });
};

