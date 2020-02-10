odoo.define('point_of_sale.CashierName', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { PosComponent } = require('point_of_sale.PosComponent');

    // Previously UsernameWidget
    class CashierName extends PosComponent {
        get username() {
            const cashier = this.env.pos.get_cashier();
            if (cashier) {
                return cashier.name;
            } else {
                return '';
            }
        }
    }

    Chrome.addComponents([CashierName]);

    return { CashierName };
});
