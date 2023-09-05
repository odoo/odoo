odoo.define('pos_sale_gift_card.models', function (require) {
    "use strict";

    var { Order } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const PosSaleGiftCard = (Order) => class PosSaleGiftCardOrder extends Order {
        set_orderline_options(line, options) {
            super.set_orderline_options(...arguments);
            if (options.gift_card_id) {
                line.gift_card_id = options.gift_card_id;
            }
        }
    }
    Registries.Model.extend(Order, PosSaleGiftCard);
});
