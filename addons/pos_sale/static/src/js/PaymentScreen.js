odoo.define('pos_sale.PosSalePaymentScreen', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');

    const PosSalePaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            toggleIsToInvoice() {
                if(this.isSaleOrder()) {
                    this.showPopup('ErrorPopup',{
                        'title': this.env._t('Invoice Required'),
                        'body':  this.env._t('An invoice is required to complete a sale order.'),
                    });
                } else {
                    super.toggleIsToInvoice();
                }
            }
            isSaleOrder() {
                let lines = this.currentOrder.get_orderlines();
                for(let line of lines) {
                    if(line.sale_order_line_id) {
                        return true;
                    }
                }
                return false;
            }
        };

    Registries.Component.extend(PaymentScreen, PosSalePaymentScreen);

    return PosSalePaymentScreen;
});
