odoo.define('point_of_sale.CashierName', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

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
    CashierName.template = 'CashierName';

    Registries.Component.add(CashierName);

    return CashierName;
});
