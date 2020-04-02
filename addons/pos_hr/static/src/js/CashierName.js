odoo.define('pos_hr.CashierName', function(require) {
    'use strict';

    const { CashierName } = require('point_of_sale.CashierName');
    const Registry = require('point_of_sale.ComponentsRegistry');

    const PosHrCashierName = CashierName =>
        class extends CashierName {
            mounted() {
                this.env.pos.on('change:cashier', this.render, this);
            }
            willUnmount() {
                this.env.pos.off('change:cashier', null, this);
            }
            async selectCashier() {
                if (!this.env.pos.config.module_pos_hr) return;

                const selectionList = this.env.pos.employees
                    .filter(employee => employee.id !== this.env.pos.get_cashier().id)
                    .map(employee => {
                        return {
                            id: employee.id,
                            item: employee,
                            label: employee.name,
                            isSelected: false,
                        };
                    });
                let {
                    confirmed: confirmSelection,
                    payload: selectedEmployee,
                } = await this.showPopup('SelectionPopup', {
                    title: 'Who are you?',
                    list: selectionList,
                });

                if (!confirmSelection) return;

                if (!selectedEmployee.pin) {
                    this.env.pos.set_cashier(selectedEmployee);
                    return;
                }

                const { confirmed: confirmPin, payload: inputtedPin } = await this.showPopup(
                    'NumberPopup',
                    {
                        isPassword: true,
                        title: "What's the password?",
                        startingValue: null,
                    }
                );

                if (!confirmPin) return;

                if (selectedEmployee.pin === Sha1.hash(inputtedPin)) {
                    this.env.pos.set_cashier(selectedEmployee);
                } else {
                    await this.showPopup('ErrorPopup', {
                        title: this.env._t('Incorrect Password'),
                        body: this.env._t(
                            'The inputted password is not correct. Please try again.'
                        ),
                    });
                }
            }
        };

    Registry.extend(CashierName.name, PosHrCashierName);
});
