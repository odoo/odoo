odoo.define('pos_hr.CashierName', function (require) {
    'use strict';

    const CashierName = require('point_of_sale.CashierName');
    const Registries = require('point_of_sale.Registries');
    const useSelectEmployee = require('pos_hr.useSelectEmployee');
    const { useBarcodeReader } = require('point_of_sale.custom_hooks');

    const PosHrCashierName = (CashierName) =>
        class extends CashierName {
            constructor() {
                super(...arguments);
                const { selectEmployee, askPin } = useSelectEmployee();
                this.askPin = askPin;
                this.selectEmployee = selectEmployee;
                useBarcodeReader({ cashier: this._onCashierScan });
            }
            mounted() {
                this.env.pos.on('change:cashier', this.render, this);
            }
            willUnmount() {
                this.env.pos.off('change:cashier', null, this);
            }
            async selectCashier() {
                if (!this.env.pos.config.module_pos_hr) return;

                const list = this.env.pos.employees
                    .filter((employee) => employee.id !== this.env.pos.get_cashier().id)
                    .map((employee) => {
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
                }
            }
            async _onCashierScan(code) {
                const employee = this.env.pos.employees.find(
                    (emp) => emp.barcode === Sha1.hash(code.code)
                );

                if (!employee || employee === this.env.pos.get_cashier()) return;

                if (!employee.pin || (await this.askPin(employee))) {
                    this.env.pos.set_cashier(employee);
                }
            }
        };

    Registries.Component.extend(CashierName, PosHrCashierName);

    return CashierName;
});
