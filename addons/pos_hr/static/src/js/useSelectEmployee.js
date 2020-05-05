odoo.define('pos_hr.useSelectEmployee', function (require) {
    'use strict';

    const { Component } = owl;

    function useSelectEmployee() {
        const current = Component.current;

        async function askPin(employee) {
            const { confirmed, payload: inputPin } = await this.showPopup('NumberPopup', {
                isPassword: true,
                title: this.env._t('Password ?'),
                startingValue: null,
            });

            if (!confirmed) return false;

            if (employee.pin === Sha1.hash(inputPin)) {
                return employee;
            } else {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Incorrect Password'),
                });
                return false;
            }
        }

        async function selectEmployee(selectionList) {
            const { confirmed, payload: employee } = await this.showPopup('SelectionPopup', {
                title: this.env._t('Change Cashier'),
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
