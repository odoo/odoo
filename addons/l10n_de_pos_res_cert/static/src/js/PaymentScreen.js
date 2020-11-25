odoo.define('l10n_de_pos_res_cert.PaymentScreen', function(require) {
    "use strict";

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');


    const PosDeResPaymentScreen = PaymentScreen => class extends PaymentScreen {
        //@Override
        async validateOrder(isForceValidate) {
            if (this.env.pos.isRestaurantCountryGermany()) {
                await this.rpc({
                    model: 'pos.order',
                    method: 'retrieve_line_difference',
                    args: [this.currentOrder.exportOrderLinesAsJson()]
                }).then(async data => {
                    if (data.differences.length > 0) {
                        await this.currentOrder.createAndFinishOrderTransaction(data.differences);
                    }
                });
            }
            await super.validateOrder(...arguments);
        }
    };

    Registries.Component.extend(PaymentScreen, PosDeResPaymentScreen);

    return PosDeResPaymentScreen;
});
