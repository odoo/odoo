odoo.define('l10n_sa_edi_pos.PaymentScreen', function(require) {
    "use strict";

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');


    const PosSAPaymentScreen = PaymentScreen => class extends PaymentScreen {
        //@Override
        toggleIsToInvoice() {
            // If the company is Saudi, POS orders should always be Invoiced
            if (this.currentOrder.pos.company.country && this.currentOrder.pos.company.country.code === 'SA') return false
            return super.toggleIsToInvoice(...arguments);
        }
    };

    Registries.Component.extend(PaymentScreen, PosSAPaymentScreen);

    return PosSAPaymentScreen;
})