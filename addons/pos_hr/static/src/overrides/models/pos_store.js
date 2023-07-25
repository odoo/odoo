/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, "pos_hr.PosStore", {
    async setup() {
        await this._super(...arguments);
        if (this.config.module_pos_hr) {
            this.showTempScreen("LoginScreen");
        }
    },
    async _processData(loadedData) {
        await this._super(...arguments);
        if (this.config.module_pos_hr) {
            this.employees = loadedData["hr.employee"];
            this.employee_by_id = loadedData["employee_by_id"];
            this.reset_cashier();
        }
    },
    async after_load_server_data() {
        await this._super(...arguments);
        if (this.config.module_pos_hr) {
            this.hasLoggedIn = !this.config.module_pos_hr;
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
    },
    set_cashier(employee) {
        this.cashier = employee;
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
        return this._super(...arguments);
    },
    get_cashier_user_id() {
        if (this.config.module_pos_hr) {
            return this.cashier.user_id ? this.cashier.user_id : null;
        }
        return this._super(...arguments);
    },
    async logEmployeeMessage(action, message) {
        if (!this.config.module_pos_hr) {
            this._super(...arguments);
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
            return this._super(...arguments) && this.hasLoggedIn;
        }
        return this._super(...arguments);
    },
});
