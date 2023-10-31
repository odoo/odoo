odoo.define('pos_sale_gift_card.models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var super_order_model = models.Order.prototype;

    models.Order = models.Order.extend({
        set_orderline_options: function (line, options) {
            super_order_model.set_orderline_options.apply(this, arguments);
            if (options.gift_card_id) {
                line.gift_card_id = options.gift_card_id;
            }
        },
    });

});
