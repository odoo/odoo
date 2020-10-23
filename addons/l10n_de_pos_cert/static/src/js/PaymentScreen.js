odoo.define('l10n_de_pos_cert.PaymentScreen', function(require) {
    "use strict";

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const Api = require('l10n_de_pos_cert.Api');



    const PosDePaymentScreen = PaymentScreen => class extends PaymentScreen {
        async _preShowScreen() {
            console.log("Hey test");
            await Api.createTransaction(this.currentOrder);
            await Api.finishShortTransaction(this.currentOrder);

        }
    };

    Registries.Component.extend(PaymentScreen, PosDePaymentScreen);

    return PaymentScreen;
});
