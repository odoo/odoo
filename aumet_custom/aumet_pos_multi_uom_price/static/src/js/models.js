odoo.define('pos_multi_uom_price.models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var _super_orderline = models.Orderline.prototype;

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
        initialize: function (attr, options) {
            _super_orderline.initialize.call(this, attr, options);
            this.product_uom_id = this.product_uom_id || this.product.uom_id;
        },
        export_as_JSON: function () {
            var json = _super_orderline.export_as_JSON.call(this);
            json.product_uom_id = this.product_uom_id[0];
            return json;
        },
        init_from_JSON: function (json) {
            _super_orderline.init_from_JSON.apply(this, arguments);
            this.product_uom_id = {
                0: this.pos.units_by_id[json.product_uom_id].id,
                1: this.pos.units_by_id[json.product_uom_id].name
            };
        },
        set_uom: function (uom_id) {
            this.product_uom_id = uom_id;
            this.trigger('change', this);
        },
    });

});

