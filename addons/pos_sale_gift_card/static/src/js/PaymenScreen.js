odoo.define('pos_sale_gift_card.PaymentScreen', function (require) {
    "use strict";
    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const PosSaleGiftCardPaymentScreen = PosGiftCardPaymentScreen => class extends PosGiftCardPaymentScreen {
        async isGiftCardValid(line) {
            let is_valid = await this.rpc({
                model: "gift.card",
                method: 'can_be_used_in_pos',
                args: [line.gift_card_id, line.sale_order_origin_id],
              });
            return is_valid;
        }
    };

    Registries.Component.extend(PaymentScreen, PosSaleGiftCardPaymentScreen);

    return PosSaleGiftCardPaymentScreen;
});
