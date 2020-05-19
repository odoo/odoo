odoo.define('point_of_sale.SelectEmployeePopup', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const SelectionPopup = require('point_of_sale.SelectionPopup');
    const useSelectEmployee = require('pos_hr.useSelectEmployee');
    const { useBarcodeReader } = require('point_of_sale.custom_hooks');

    const SelectEmployeePopup = (SelectionPopup) => {
        class SelectEmployeePopup extends SelectionPopup {
            constructor() {
                super(...arguments);
                const { askPin } = useSelectEmployee();
                this.askPin = askPin;
                useBarcodeReader({ cashier: this._onCashierScan });
            }
            async _onCashierScan(code) {
                const employee = this.env.pos.employees.find(
                    (emp) => emp.barcode === Sha1.hash(code.code)
                );

                if (!employee || employee === this.env.pos.get_cashier()) {
                    this.cancel();
                    return;
                }

                if (!employee.pin || (await this.askPin(employee))) {
                    this.env.pos.set_cashier(employee);
                }
                this.cancel();
            }
        }
        SelectEmployeePopup.template = 'SelectEmployeePopup';
        return SelectEmployeePopup;
    };

    Registries.Component.addByExtending(SelectEmployeePopup, SelectionPopup);

    return SelectEmployeePopup;
});
