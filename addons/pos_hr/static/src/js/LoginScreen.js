odoo.define('pos_hr.LoginScreen', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const useSelectEmployee = require('pos_hr.useSelectEmployee');
    const { useBarcodeReader } = require('point_of_sale.custom_hooks');

    class LoginScreen extends PosComponent {
        constructor() {
            super(...arguments);
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
