/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        if (this.config.module_pos_hr) {
            if (!this.hasLoggedIn) {
                this.showTempScreen("LoginScreen");
            }
        }
    },
    async _processData(loadedData) {
        await super._processData(...arguments);
        if (this.config.module_pos_hr) {
            this.employees = loadedData["hr.employee"];
            this.employee_by_id = loadedData["employee_by_id"];
            const saved_cashier_id = sessionStorage.getItem("connected_cashier");
            if (saved_cashier_id) {
                this.set_cashier(this.employee_by_id[saved_cashier_id]);
            } else {
                this.reset_cashier();
            }
        }
    },
    async after_load_server_data() {
        await super.after_load_server_data(...arguments);
        if (this.config.module_pos_hr) {
            const saved_cashier = sessionStorage.getItem("connected_cashier");
            this.hasLoggedIn = saved_cashier ? true : false;
        }
    },
    reset_cashier() {
        this.cashier = {
            name: null,
            id: null,
            barcode: null,
            user_id: null,
            pin: null,
            role: null,
        };
        sessionStorage.removeItem("connected_cashier");
    },
    set_cashier(employee) {
        this.cashier = employee;
        sessionStorage.setItem("connected_cashier", employee.id);
        const selectedOrder = this.get_order();
        if (selectedOrder && !selectedOrder.get_orderlines().length) {
            // Order without lines can be considered to be un-owned by any employee.
            // We set the cashier on that order to the currently set employee.
            selectedOrder.cashier = employee;
        }
        if (!this.cashierHasPriceControlRights() && this.numpadMode === "price") {
            this.numpadMode = "quantity";
        }
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
        await this.orm.call("pos.session", "log_partner_message", [
            this.pos_session.id,
            this.cashier.work_contact_id,
            action,
            message,
        ]);
    },

    /**
     * @override
     */
    shouldShowCashControl() {
        if (this.config.module_pos_hr) {
            return super.shouldShowCashControl(...arguments) && this.hasLoggedIn;
        }
        return super.shouldShowCashControl(...arguments);
    },
});
