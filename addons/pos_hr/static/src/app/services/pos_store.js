/* global Sha1 */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { _t } from "@web/core/l10n/translation";
import { makeAwaitable, ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { browser } from "@web/core/browser/browser";
import { CashierSelectionPopup } from "@pos_hr/app/components/popups/cashier_selection_popup/cashier_selection_popup";

patch(PosStore.prototype, {
    async setup() {
        this.employeeBuffer = [];
        await super.setup(...arguments);
        if (this.config.module_pos_hr) {
            this.login = Boolean(odoo.from_backend) && !this.config.module_pos_hr;
            if (!this.accessRight.hasLoggedIn()) {
                this.navigate("LoginScreen");
            }
        }
        browser.addEventListener("online", () => {
            if (this.session?.id) {
                this.employeeBuffer.forEach((employee) =>
                    this.data.write("pos.session", [this.session.id], {
                        employee_id: employee.id,
                    })
                );
            }
            this.employeeBuffer = [];
        });
    },
    get employeeIsAdmin() {
        const cashier = this.accessRight.loggedCashier;
        return cashier._role === "manager";
    },
    async afterProcessServerData() {
        await super.afterProcessServerData(...arguments);
        if (this.config.module_pos_hr) {
            const saved_cashier = this.accessRight._getConnectedCashier();
            this.accessRight.hasLoggedIn.set(saved_cashier ? true : false);
        }
    },
    createNewOrder() {
        const order = super.createNewOrder(...arguments);

        if (this.config.module_pos_hr) {
            order.employee_id = this.accessRight.loggedCashier;
        }

        return order;
    },
    setCashier(employee) {
        super.setCashier(employee);

        if (this.config.module_pos_hr) {
            if (!this.data.network.offline && this.session?.id) {
                this.data.write("pos.session", [this.session.id], {
                    employee_id: employee.id,
                });
            } else {
                this.employeeBuffer.push(employee);
            }
            const o = this.getOrder();
            if (o && !o.getOrderlines().length) {
                // Order without lines can be considered to be un-owned by any employee.
                // We set the cashier on that order to the currently set employee.
                o.employee_id = employee;
            }
            if (this.accessRight.disablePriceButton && this.numpadMode === "price") {
                this.numpadMode = "quantity";
            }
        }
    },
    checkPreviousLoggedCashier() {
        if (this.config.module_pos_hr) {
            const savedCashier = this.accessRight._getConnectedCashier();
            if (savedCashier) {
                this.setCashier(savedCashier);
            } else {
                this.accessRight.resetCashier();
            }
        } else {
            super.checkPreviousLoggedCashier(...arguments);
        }
    },
    async selectCashier(pin = false, login = false, list = false) {
        if (!this.config.module_pos_hr) {
            return;
        }

        const wrongPinNotification = () => {
            this.notification.add(_t("PIN not found"), {
                type: "warning",
                title: _t(`Wrong PIN`),
            });
        };

        let employee = false;
        const allEmployees = this.models["hr.employee"].filter(
            (employee) => employee.id !== this.accessRight.loggedCashier?.id
        );
        const pinMatchEmployees = allEmployees.filter(
            (employee) => !pin || Sha1.hash(pin) === employee._pin
        );

        if (!pinMatchEmployees.length && !pin) {
            await ask(this.dialog, {
                title: _t("No Cashiers"),
                body: _t("There is no cashier available."),
            });
            return;
        } else if (pin && !pinMatchEmployees.length) {
            wrongPinNotification();
            return;
        }

        if (pinMatchEmployees.length > 1 || list) {
            employee = await makeAwaitable(this.dialog, CashierSelectionPopup, {
                currentCashier: this.accessRight.loggedCashier || undefined,
                employees: this.accessRight.getCashierSelectionList(allEmployees),
            });

            if (!employee) {
                return;
            }

            if (pin && Sha1.hash(pin) !== employee._pin) {
                wrongPinNotification();
                return;
            }
        } else if (pinMatchEmployees.length === 1) {
            employee = pinMatchEmployees[0];
        }

        if (!pin && employee && employee._pin) {
            const result = await this.accessRight.checkPin(employee);

            if (!result) {
                return false;
            }
        }

        if (login && employee) {
            this.accessRight.hasLoggedIn.set(true);
            this.setCashier(employee);
        }

        const currentScreen = this.router.currentScreen();
        if (currentScreen === "LoginScreen" && login && employee) {
            const selectedScreen = this.defaultPage;
            const props = {
                ...selectedScreen?.params,
            };
            this.router.navigate(selectedScreen.page, props);
        }

        return employee;
    },
    addLineToCurrentOrder(vals, opt = {}, configure = true) {
        vals.employee_id = false;

        if (this.config.module_pos_hr) {
            const cashier = this.accessRight.loggedCashier;

            if (cashier && cashier.model.name === "hr.employee") {
                const order = this.getOrder();
                order.employee_id = this.accessRight.loggedCashier;
            }
        }

        return super.addLineToCurrentOrder(vals, opt, configure);
    },
    /**{name: null, id: null, barcode: null, user_id:null, pin:null}
     * If pos_hr is activated, return {name: string, id: int, barcode: string, pin: string, user_id: int}
     * @returns {null|*}
     */
    getSyncAllOrdersContext(orders, options = {}) {
        const context = super.getSyncAllOrdersContext(orders, options);
        const cashier = this.accessRight.loggedCashier;
        if (cashier?.id) {
            context.current_cashier_id = cashier.id;
        }
        return context;
    },
    async logEmployeeMessage(action, message) {
        if (!this.config.module_pos_hr) {
            super.logEmployeeMessage(...arguments);
            return;
        }
        await this.data.call("pos.session", "log_partner_message", [
            this.session.id,
            this.accessRight.cashier.work_contact_id?.id,
            action,
            message,
        ]);
    },
    /**
     * @override
     */
    shouldShowOpeningControl() {
        if (this.config.module_pos_hr) {
            return super.shouldShowOpeningControl(...arguments) && this.accessRight.hasLoggedIn();
        }
        return super.shouldShowOpeningControl(...arguments);
    },
    get hasProductCreationAccess() {
        return this.config.module_pos_hr
            ? this.employeeIsAdmin && super.hasProductCreationAccess
            : super.hasProductCreationAccess;
    },
    canEditPayment(order) {
        return super.canEditPayment(order) && (!this.config.module_pos_hr || this.employeeIsAdmin);
    },
    async handleUrlParams() {
        if (this.config.module_pos_hr && !this.accessRight.cashier) {
            if (this.router.currentScreen() !== "LoginScreen") {
                this.router.navigate("LoginScreen", {});
            }
            return;
        }
        return await super.handleUrlParams(...arguments);
    },
});
