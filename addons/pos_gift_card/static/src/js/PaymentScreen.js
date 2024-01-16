odoo.define('pos_gift_card.PaymentScreen', function(require) {
    "use strict";

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    var core = require('web.core');
    var _t = core._t;


    const PosGiftCardPaymentScreen = PaymentScreen => class extends PaymentScreen {
        //@Override
        async validateOrder(isForceValidate) {
            if(this.env.pos.config.use_gift_card) {
                if (await this._isOrderValid(isForceValidate)) {
                    try {
                        let giftProduct = this.env.pos.db.product_by_id[this.env.pos.config.gift_card_product_id[0]];

                        for (let line of this.currentOrder.orderlines.models) {
                            if(line.product.id === giftProduct.id && line.price <= 0) {
                                let is_valid = await this.isGiftCardValid(line);
                                if(!is_valid) {
                                    await this.showPopup('ErrorPopup', {
                                        'title': _t("Gift Card Error"),
                                        'body': _t("Gift card is not valid."),
                                    });
                                    return;
                                }

                                let gift_card = await this.rpc({
                                    model: "gift.card",
                                    method: 'search_read',
                                    domain: [['id', '=', line.gift_card_id]],
                                    fields: ['balance'],
                                  });

                                if(Math.abs(line.get_unit_price()) > gift_card[0].balance) {
                                    await this.showPopup('ErrorPopup', {
                                        'title': _t("Gift Card Error"),
                                        'body': _t("Gift card balance is too low."),
                                    });
                                    return;
                                }
                            }
                        }
                    } catch (e) {
                        // do nothing with the error
                    }
                } else {
                    return; // do nothing if the order is not valid
                }
            }
            await super.validateOrder(...arguments);
        }

        async _postPushOrderResolve(order, server_ids) {
            if(this.env.pos.config.use_gift_card) {
                let ids = await this.rpc({
                    model: 'pos.order',
                    method: 'get_new_card_ids',
                    args: [server_ids]
                });
                if(ids.length > 0)
                    this.env.pos.print_gift_pdf(ids);
            }
            return super._postPushOrderResolve(order, server_ids);
        }

        async isGiftCardValid(line) {
            let is_valid = await this.rpc({
                model: "gift.card",
                method: 'can_be_used_in_pos',
                args: [line.gift_card_id],
              });
            return is_valid;
        }
    };

    Registries.Component.extend(PaymentScreen, PosGiftCardPaymentScreen);

    return PosGiftCardPaymentScreen;
});
