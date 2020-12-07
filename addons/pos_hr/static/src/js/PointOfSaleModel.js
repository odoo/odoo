odoo.define('pos_hr.PointOfSaleModel', function (require) {
    'use strict';

    const PointOfSaleModel = require('point_of_sale.PointOfSaleModel');
    const { patch } = require('web.utils');
    const { _t } = require('web.core');

    patch(PointOfSaleModel.prototype, 'pos_hr', {
        //#region OVERRIDES

        _initDataUiState() {
            const result = this._super();
            result.LoginScreen = { prevScreen: null };
            return result;
        },
        async loadPosData() {
            await this._super(...arguments);
            const employees = this.getRecords('hr.employee');
            if (!employees.length) {
                // Force-disable `module_pos_hr` if no employees are loaded.
                this.config.module_pos_hr = false;
            }
            const hashedEmployeeData = await this._rpc({
                model: 'hr.employee',
                method: 'get_barcodes_and_pin_hashed',
                args: [employees.map((employee) => employee.id)],
            });
            for (const employee of employees) {
                employee._extras = {};
                employee._extras.hashedPin = hashedEmployeeData[employee.id].pin;
                employee._extras.hashedBarcode = hashedEmployeeData[employee.id].barcode;
            }
        },
        /**
         * We save the previous screen before showing the login screen.
         * This information will be used to determine the screen to show after
         * a successful login. @see _getScreenAfterLogin
         *
         * Also, we want to deselect the currently activeEmployee.
         */
        async beforeChangeScreen(prevScreen, newScreen) {
            if (newScreen === 'LoginScreen') {
                this.data.uiState.LoginScreen.prevScreen = prevScreen;
                this.data.uiState.activeEmployeeId = undefined;
            }
            await this._super(...arguments);
        },
        /**
         * Replace the employee in the order if it originally has no orderlines.
         * This means that the currently active employee will automatically be assign
         * to the empty order.
         */
        async actionAddProduct(order) {
            if (!order.lines.length) {
                order.employee_id = this.data.uiState.activeEmployeeId;
            }
            return this._super(...arguments);
        },
        _createDefaultOrder() {
            const newOrder = this._super(...arguments);
            newOrder.employee_id = this.data.uiState.activeEmployeeId;
            return newOrder;
        },
        _getStartScreens(activeOrder) {
            const result = this._super(...arguments);
            if (this.config.module_pos_hr) {
                result.push(['LoginScreen', 0]);
            }
            return result;
        },
        /**
         * This override augments the method to identify if the active cashier is a manager.
         */
        getIsCashierManager() {
            const cashier = this.getActiveCashier();
            if (!cashier) {
                return this._super(...arguments);
            }
            return cashier.user_id === this.user.id && this._super(...arguments);
        },
        /**
         * When this module is installed, a cashier is represented by an employee.
         * We derive the cashier name from the employee instead of the logged in user.
         */
        getCashierName() {
            const activeCashier = this.getActiveCashier();
            if (!activeCashier) return this._super(...arguments);
            return activeCashier.name;
        },

        //#endregion OVERRIDES

        /**
         * Shows a number dialog to ask the pin of the given employee.
         * @param {'hr.employee'} employee
         * @returns {[true, 'hr.employee'] | [false, string | undefined]}
         */
        async _verifyPin(employee) {
            if (!employee._extras.hashedPin) return [true, employee];
            const [confirmed, inputPin] = await this.ui.askUser('NumberPopup', {
                isPassword: true,
                title: employee.name,
                startingValue: null,
            });
            if (!confirmed) return [false];
            if (employee._extras.hashedPin === Sha1.hash(inputPin)) {
                return [true, employee];
            } else {
                return [false, _t('Incorrect Password')];
            }
        },
        /**
         * From a selection list of employees, this method asks the user
         * which employee to select.
         * @param {{ id: string, label: string }[]} selectionList
         * @returns {[true, 'hr.employee'] | [false, string | undefined]}
         */
        async _selectEmployee(selectionList) {
            const [confirmed, selected] = await this.ui.askUser('SelectionPopup', {
                title: _t('Change Cashier'),
                list: selectionList,
            });
            if (!confirmed) return [false];
            const selectedEmployee = this.getRecord('hr.employee', selected.id);
            if (!selectedEmployee._extras.hashedPin || selected.id === this.data.uiState.activeEmployeeId) {
                return [true, selectedEmployee];
            }
            return await this._verifyPin(selectedEmployee);
        },
        /**
         * If `selected` is given, it is an employee and it is verified.
         * If `selectionList` is given, it asks user to select from the list and verify the selection.
         * Then shows the proper screen when selection of employee is successful.
         * @param {{ selectionList: { id: string, label: string }[], selected: 'hr.employee' }} param0
         */
        async actionSelectEmployee({ selectionList, selected }) {
            let successful, payload;
            if (selected) {
                [successful, payload] = await this._verifyPin(selected);
            } else if (selectionList) {
                [successful, payload] = await this._selectEmployee(selectionList);
            }
            if (successful) {
                // payload is employee
                const previousActiveEmployeeId = this.data.uiState.activeEmployeeId;
                const selectedEmployee = this.getRecord('hr.employee', payload.id);
                this.data.uiState.activeEmployeeId = payload.id;
                await this.actionShowScreen(this._getScreenAfterLogin());
                if (previousActiveEmployeeId !== payload.id) {
                    this.ui.showNotification(_.str.sprintf(_t('Logged in as %s'), selectedEmployee.name));
                }
            } else {
                // payload is the error message
                if (payload) {
                    this.ui.askUser('ErrorPopup', {
                        title: _t('Login Error'),
                        body: payload,
                    });
                }
            }
        },
        _getScreenAfterLogin() {
            const prevScreen = this.data.uiState.LoginScreen.prevScreen;
            if (prevScreen && !this._shouldSetScreenToOrder(prevScreen)) {
                return prevScreen;
            }
            const activeOrder = this.getActiveOrder();
            return this.getOrderScreen(activeOrder);
        },
        getActiveCashier() {
            return this.getRecord('hr.employee', this.data.uiState.activeEmployeeId);
        },
        _shouldTriggerAfterIdleCallback() {
            if (this.getActiveScreen() === 'LoginScreen') {
                return false;
            } else {
                return this._super(...arguments);
            }
        },
    });

    return PointOfSaleModel;
});
