odoo.define('pos_six.BalanceButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class BalanceButton extends PosComponent {
        sendBalance() {
            this.env.pos.payment_methods.map(pm => {
                if (pm.use_payment_terminal === 'six') {
                    pm.payment_terminal.send_balance();
                }
            });
        }
    }
    BalanceButton.template = 'BalanceButton';

    Registries.Component.add(BalanceButton);

    return BalanceButton;
});
