odoo.define('pos_hr.PaymentScreen', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');

    const PosHrPaymentScreen = (PaymentScreen_) =>
          class extends PaymentScreen_ {
              async _finalizeValidation() {
                  this.currentOrder.employee = this.env.pos.get_cashier();
                  await super._finalizeValidation();
              }
          };

    Registries.Component.extend(PaymentScreen, PosHrPaymentScreen);

    return PaymentScreen;
});
