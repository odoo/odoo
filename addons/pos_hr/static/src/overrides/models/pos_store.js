import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { browser } from "@web/core/browser/browser";

patch(PosStore.prototype, {
    async setup() {
        this.employeeBuffer = [];
        await super.setup(...arguments);
        if (this.config.module_pos_hr) {
            this.login = Boolean(odoo.from_backend) && !this.config.module_pos_hr;
            if (!this.hasLoggedIn) {
                this.showScreen("LoginScreen");
            }
        }
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
        const cashier = this.get_cashier();
        return cashier._role === "manager";
    },
    checkPreviousLoggedCashier() {
        if (this.config.module_pos_hr) {
            const savedCashier = this._getConnectedCashier();
            if (savedCashier) {
                this.set_cashier(savedCashier);
            } else {
                this.reset_cashier();
            }
        } else {
            super.checkPreviousLoggedCashier(...arguments);
        }
    },
    async afterProcessServerData() {
        await super.afterProcessServerData(...arguments);
        if (this.config.module_pos_hr) {
            const saved_cashier = this._getConnectedCashier();
            this.hasLoggedIn = saved_cashier ? true : false;
        }
    },
    createNewOrder() {
        const order = super.createNewOrder(...arguments);

        if (this.config.module_pos_hr) {
            order.update({ employee_id: this.get_cashier() });
        }

        return order;
    },
    set_cashier(employee) {
        super.set_cashier(employee);

        if (this.config.module_pos_hr) {
            if (navigator.onLine) {
                this.data.write("pos.session", [this.config.current_session_id.id], {
                    employee_id: employee.id,
                });
            } else {
                this.employeeBuffer.push(employee);
            }
            const o = this.get_order();
            if (o && !o.get_orderlines().length) {
                // Order without lines can be considered to be un-owned by any employee.
                // We set the cashier on that order to the currently set employee.
                o.update({ employee_id: employee });
            }
            if (!this.cashierHasPriceControlRights() && this.numpadMode === "price") {
                this.numpadMode = "quantity";
            }
        }
    },
    addLineToCurrentOrder(vals, opt = {}, configure = true) {
        vals.employee_id = false;

        if (this.config.module_pos_hr) {
            const cashier = this.get_cashier();

            if (cashier && cashier.model.modelName === "hr.employee") {
                const order = this.get_order();
                order.update({ employee_id: this.get_cashier() });
            }
        }

        return super.addLineToCurrentOrder(vals, opt, configure);
    },
    /**{name: null, id: null, barcode: null, user_id:null, pin:null}
     * If pos_hr is activated, return {name: string, id: int, barcode: string, pin: string, user_id: int}
     * @returns {null|*}
     */
    get_cashier() {
        if (this.config.module_pos_hr) {
            return this.cashier;
        }
        return super.get_cashier(...arguments);
    },
    get_cashier_user_id() {
        if (this.config.module_pos_hr) {
            return this.cashier.user_id ? this.cashier.user_id : null;
        }
        return super.get_cashier_user_id(...arguments);
    },
    async logEmployeeMessage(action, message) {
        if (!this.config.module_pos_hr) {
            super.logEmployeeMessage(...arguments);
            return;
        }
        await this.data.call("pos.session", "log_partner_message", [
            this.session.id,
            this.cashier.work_contact_id?.id,
            action,
            message,
        ]);
    },
    _getConnectedCashier() {
        if (!this.config.module_pos_hr) {
            return super._getConnectedCashier(...arguments);
        }
        const cashier_id = Number(sessionStorage.getItem(`connected_cashier_${this.config.id}`));
        if (cashier_id && this.models["hr.employee"].get(cashier_id)) {
            return this.models["hr.employee"].get(cashier_id);
        }
        return false;
    },

    /**
     * @override
     */
    shouldShowOpeningControl() {
        if (this.config.module_pos_hr) {
            return super.shouldShowOpeningControl(...arguments) && this.hasLoggedIn;
        }
        return super.shouldShowOpeningControl(...arguments);
    },
    async allowProductCreation() {
        if (this.config.module_pos_hr) {
            return this.employeeIsAdmin && (await super.allowProductCreation());
        }
        return await super.allowProductCreation();
    },
});
