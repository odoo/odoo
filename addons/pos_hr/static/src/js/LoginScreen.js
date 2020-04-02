odoo.define('point_of_sale.LoginScreen', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { PosComponent, addComponents } = require('point_of_sale.PosComponent');

    class LoginScreen extends PosComponent {
        mounted() {
            if (this.env.pos.barcode_reader) {
                this.env.pos.barcode_reader.set_action_callback(
                    'cashier',
                    this._barcodeCashierAction.bind(this)
                );
            }
        }
        willUnmount() {
            if (this.env.pos.barcode_reader) {
                this.env.pos.barcode_reader.remove_action_callback('cashier');
            }
        }
        back() {
            this.props.resolve({ confirmed: false, payload: false });
            this.trigger('close-temp-screen');
        }
        confirm() {
            this.props.resolve({ confirmed: true, payload: true });
            this.trigger('close-temp-screen');
        }
        get shopName() {
            return this.env.pos.config.name;
        }
        closeSession() {
            this.trigger('close-pos');
        }
        async selectCashier() {
            const selectionList = this.env.pos.employees.map(employee => {
                return {
                    id: employee.id,
                    item: employee,
                    label: employee.name,
                    isSelected: false,
                };
            });
            let { confirmed: confirmSelection, payload: selectedEmployee } = await this.showPopup(
                'SelectionPopup',
                {
                    title: 'Who are you?',
                    list: selectionList,
                }
            );

            if (!confirmSelection) return;

            if (!selectedEmployee.pin) {
                this.env.pos.set_cashier(selectedEmployee);
                this.back();
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
                this.back();
            } else {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Incorrect Password'),
                    body: this.env._t('The inputted password is not correct. Please try again.'),
                });
            }
        }
        async _barcodeCashierAction(code) {
            let theEmployee;
            for (let employee of this.env.pos.employees) {
                if (employee.barcode === Sha1.hash(code.code)) {
                    theEmployee = employee;
                    break;
                }
            }

            if (!theEmployee.pin) {
                this.env.pos.set_cashier(theEmployee);
                this.back();
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

            if (theEmployee.pin === Sha1.hash(inputtedPin)) {
                this.env.pos.set_cashier(theEmployee);
                this.back();
            } else {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Incorrect Password'),
                    body: this.env._t('The inputted password is not correct. Please try again.'),
                });
            }
        }
    }

    // register screen component
    addComponents(Chrome, [LoginScreen]);

    return { LoginScreen };
});
