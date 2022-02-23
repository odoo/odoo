/* global Sha1 */
odoo.define('pos_hr.LoginScreen', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const TemporaryScreenMixin = require('@point_of_sale/js/Misc/TemporaryScreenMixin')[Symbol.for('default')];
    const Registries = require('point_of_sale.Registries');
    const useSelectEmployee = require('pos_hr.useSelectEmployee');
    const { useBarcodeReader } = require('point_of_sale.custom_hooks');

    class LoginScreen extends TemporaryScreenMixin(PosComponent) {
        setup() {
            super.setup();
            const { selectEmployee, askPin } = useSelectEmployee();
            this.selectEmployee = selectEmployee;
            this.askPin = askPin;
            useBarcodeReader(
                {
                    cashier: this._barcodeCashierAction,
                },
                true
            );
        }
        back() {
            this.closeWith(false);
            this.env.pos.hasLoggedIn = true;
            this.env.posbus.trigger('start-cash-control');
        }
        get shopName() {
            return this.env.pos.config.name;
        }
        async selectCashier() {
            const list = this.env.pos.employees.map((employee) => {
                return {
                    id: employee.id,
                    item: employee,
                    label: employee.name,
                    isSelected: false,
                };
            });

            const employee = await this.selectEmployee(list);
            if (employee) {
                this.env.pos.set_cashier(employee);
                this.back();
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

            if (!theEmployee) return;

            if (!theEmployee.pin || (await this.askPin(theEmployee))) {
                this.env.pos.set_cashier(theEmployee);
                this.back();
            }
        }
    }
    LoginScreen.template = 'LoginScreen';

    Registries.Component.add(LoginScreen);

    return LoginScreen;
});
