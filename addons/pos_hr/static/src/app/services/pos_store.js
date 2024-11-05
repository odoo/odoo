import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { browser } from "@web/core/browser/browser";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        if (this.config.module_pos_hr) {
            this.checkPreviousLoggedCashier();
            if (!this.cashier.logged) {
                this.showScreen("LoginScreen");
            }
        }
        this.employeeBuffer = [];
        browser.addEventListener("online", () => {
            this.employeeBuffer.forEach((employee) =>
                this.data.write("pos.session", [this.config.current_session_id.id], {
                    employee_id: employee.id,
                })
            );
            this.employeeBuffer = [];
        });
    },
    get employeeIsAdmin() {
        const employee = this.cashier.employee;
        return employee._role === "manager" || employee.user_id?.id === this.user.id;
    },
    get sessionCashierInfo() {
        if (!this.config.module_pos_hr) {
            return super.sessionCashierInfo;
        }

        return Object.assign(super.sessionCashierInfo, {
            employee: this.models["hr.employee"].get(
                sessionStorage.getItem(`connected_employee_${this.config.id}`)
            ),
        });
    },
    setSessionCashierInfo(data) {
        super.setSessionCashierInfo(...arguments);
        if ("employeeId" in data) {
            sessionStorage.setItem(`connected_employee_${this.config.id}`, data.employeeId);
        }
    },
    checkPreviousLoggedCashier() {
        const savedEmployee = this.getConnectedEmployee();
        if (savedEmployee) {
            this.set_cashier(savedEmployee);
        } else {
            this.reset_cashier();
        }
    },
    reset_cashier() {
        super.reset_cashier(...arguments);
        this.setSessionCashierInfo({ employeeId: false });
        this.cashier.employee = null;
    },
    async actionAfterIdle() {
        if (this.mainScreen.component?.name !== "LoginScreen") {
            return super.actionAfterIdle();
        }
    },
    async afterProcessServerData() {
        await super.afterProcessServerData(...arguments);
        if (this.config.module_pos_hr) {
            const saved_cashier = this.getConnectedEmployee();
            this.cashier.logged = saved_cashier ? true : false;
        }
    },
    createNewOrder() {
        const order = super.createNewOrder(...arguments);

        if (this.config.module_pos_hr) {
            order.employee_id = this.cashier.employee?.id;
        }

        return order;
    },
    set_cashier(employee) {
        if (this.config.module_pos_hr) {
            if (navigator.onLine) {
                this.data.write("pos.session", [this.config.current_session_id.id], {
                    employee_id: employee.id,
                });
            } else {
                this.employeeBuffer.push(employee);
            }
            this.cashier.employee = employee;
            this.setSessionCashierInfo({ employeeId: employee.id, userId: this.user.id });
            const o = this.get_order();
            if (o && !o.get_orderlines().length) {
                // Order without lines can be considered to be un-owned by any employee.
                // We set the cashier on that order to the currently set employee.
                o.employee_id = employee;
            }
            if (!this.cashierHasPriceControlRights() && this.numpadMode === "price") {
                this.numpadMode = "quantity";
            }
        }
    },
    addLineToCurrentOrder(vals, opt = {}, configure = true) {
        vals.employee_id = false;

        if (this.config.module_pos_hr) {
            const employee = this.cashier.employee;

            if (employee) {
                const order = this.get_order();
                order.employee_id = employee;
            }
        }

        return super.addLineToCurrentOrder(vals, opt, configure);
    },
    async closePos() {
        this.setSessionCashierInfo({ employeeId: false });
        return await super.closePos(...arguments);
    },
    async logEmployeeMessage(action, message) {
        if (!this.config.module_pos_hr) {
            super.logEmployeeMessage(...arguments);
            return;
        }
        await this.data.call("pos.session", "log_partner_message", [
            this.session.id,
            this.cashier.employee?.work_contact_id?.id,
            action,
            message,
        ]);
    },
    getConnectedEmployee() {
        return this.sessionCashierInfo.employee || false;
    },

    /**
     * @override
     */
    shouldShowOpeningControl() {
        if (this.config.module_pos_hr) {
            return super.shouldShowOpeningControl(...arguments) && this.cashier.logged;
        }
        return super.shouldShowOpeningControl(...arguments);
    },
});
