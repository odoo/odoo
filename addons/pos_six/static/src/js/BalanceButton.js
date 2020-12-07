odoo.define('pos_six.BalanceButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');

    class BalanceButton extends PosComponent {
        sendBalance() {
            for (const paymentMethod of this.env.model.data.derived.paymentMethods) {
                if (paymentMethod.use_payment_terminal === 'six') {
                    const paymentTerminal = this.env.model.getPaymentTerminal(paymentMethod.id);
                    paymentTerminal.send_balance();
                }
            }
        }
    }
    BalanceButton.template = 'pos_six.BalanceButton';

    return BalanceButton;
});
