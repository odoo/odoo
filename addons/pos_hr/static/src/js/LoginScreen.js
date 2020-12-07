odoo.define('pos_hr.LoginScreen', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');

    class LoginScreen extends PosComponent {
        get shopName() {
            return this.env.model.config.name;
        }
        async onSelectCashier() {
            const selectionList = this.env.model.getRecords('hr.employee').map((employee) => {
                return {
                    id: employee.id,
                    label: employee.name,
                    isSelected: false,
                };
            });
            this.env.model.actionHandler({ name: 'actionSelectEmployee', args: [{ selectionList }]})
        }
    }
    LoginScreen.template = 'pos_hr.LoginScreen';

    return LoginScreen;
});
