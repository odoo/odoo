odoo.define('point_of_sale.CashierName', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { PosComponent, addComponents } = require('point_of_sale.PosComponent');
    const Registry = require('point_of_sale.ComponentsRegistry');

    // Previously UsernameWidget
    class CashierName extends PosComponent {
        static template = 'CashierName';
        get username() {
            const cashier = this.env.pos.get_cashier();
            if (cashier) {
                return cashier.name;
            } else {
                return '';
            }
        }
    }

    addComponents(Chrome, [CashierName]);

    Registry.add('CashierName', CashierName);

    return { CashierName };
});
