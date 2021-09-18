odoo.define('pos_multi_uom_price.models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');

    models.load_models({
        model: 'product.multi.uom.price',
        fields: ['uom_id', 'product_id', 'price'],
        loaded: function (self, uomPrice) {
            self.product_uom_price = {};
            if (uomPrice.length) {
                _.each(uomPrice, function (unit) {
                    if (!self.product_uom_price[unit.product_id[0]]) {
                        self.product_uom_price[unit.product_id[0]] = {};
                        self.product_uom_price[unit.product_id[0]].uom_id = {};
                    }
                    self.product_uom_price[unit.product_id[0]].uom_id[unit.uom_id[0]] = {
                        id: unit.uom_id[0],
                        name: unit.uom_id[1],
                        price: unit.price,
                    };
                });
            }
        },
    });


    models.Orderline = models.Orderline.extend({
        apply_uom: function () {
            var self = this;
            var orderline = self.pos.get_order().get_selected_orderline();
            var uom_id = orderline.get_custom_uom_id();
            if (uom_id) {
                var selected_uom = this.pos.units_by_id[uom_id];
                orderline.uom_id = [uom_id, selected_uom.name];
                var latest_price = orderline.get_latest_price(selected_uom, orderline.product);
                let product = orderline.product.product_tmpl_id;
                let uomPrices = []
                if (orderline.pos.product_uom_price[product])
                    uomPrices = orderline.pos.product_uom_price[product].uom_id;
                let uom_price = {'price': 0, 'found': false}
                if (uomPrices) {
                    _.each(uomPrices, function (uomPrice) {
                        if (uomPrice.name == selected_uom.name) {
                            uom_price.price = uomPrice.price;
                            uom_price.found = true;
                        }
                    });
                }
                if (uom_price.found) {
                    orderline.set_unit_price(uom_price.price);
                } else {
                    orderline.set_unit_price(latest_price);
                }
                return true
            } else {
                return false
            }
        },
    });

});

