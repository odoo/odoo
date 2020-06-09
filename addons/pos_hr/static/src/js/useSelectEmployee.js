odoo.define('pos_hr.useSelectEmployee', function (require) {
    'use strict';

    const { Component } = owl;

    function useSelectEmployee() {
        const current = Component.current;

        async function askPin(employee) {
            const { confirmed, payload: inputPin } = await current.showPopup('NumberPopup', {
                isPassword: true,
                title: current.env._t(`Pin of '${employee.name}'`),
                startingValue: null,
            });

            if (!confirmed) return false;

            if (employee.pin === Sha1.hash(inputPin)) {
                return employee;
            } else {
                await current.showPopup('ErrorPopup', {
                    title: current.env._t('Incorrect Pin'),
                });
                return false;
            }
        }

        async function selectEmployee(selectionList, options = { hideCancelButton: false }) {
            const { confirmed, payload: employee } = await current.showPopup(
                'SelectEmployeePopup',
                {
                    title: current.env._t('Select Cashier or Scan Badge'),
                    list: selectionList,
                    hideCancelButton: options.hideCancelButton,
                }
            );

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
