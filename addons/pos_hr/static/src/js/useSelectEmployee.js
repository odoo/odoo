odoo.define('pos_hr.useSelectEmployee', function (require) {
    'use strict';

    const { Component } = owl;
    const { Gui } = require('point_of_sale.Gui');

    function useSelectEmployee() {
        const current = Component.current;

        async function askPin(employee) {
            const { confirmed, payload: inputPin } = await this.showPopup('NumberPopup', {
                isPassword: true,
                title: this.env._t(`Pin of '${employee.name}'`),
                startingValue: null,
            });

            if (!confirmed) return false;

            if (employee.pin === Sha1.hash(inputPin)) {
                return employee;
            } else {
                // NOTE: This hook is used in a popup, so use
                // Gui because a popup can't show other popup.
                await Gui.showPopup('ErrorPopup', {
                    title: this.env._t('Incorrect Pin'),
                });
                return false;
            }
        }

        async function selectEmployee(selectionList) {
            const { confirmed, payload: employee } = await this.showPopup('SelectEmployeePopup', {
                title: this.env._t('Select Cashier or Scan Badge'),
                list: selectionList,
            });

            if (!confirmed) return false;

            if (!employee.pin) {
                return employee;
            }

            return await askPin.call(current, employee);
        }
        return { askPin: askPin.bind(current), selectEmployee: selectEmployee.bind(current) };
    }

    return useSelectEmployee;
});
