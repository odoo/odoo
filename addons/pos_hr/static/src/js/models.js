/** @odoo-module */

import { PosGlobalState, Order } from "@point_of_sale/js/models";
import { patch } from "@web/core/utils/patch";

patch(PosGlobalState.prototype, "pos_hr.PosGlobalState", {
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
});

patch(Order.prototype, "pos_hr.Order", {
    setup(options) {
        this._super(...arguments);
        if (!options.json && this.pos.config.module_pos_hr) {
            this.cashier = this.pos.get_cashier();
        }
    },
    init_from_JSON(json) {
        this._super(...arguments);
        if (this.pos.config.module_pos_hr && json.employee_id) {
            this.cashier = this.pos.employee_by_id[json.employee_id];
        }
    },
    export_as_JSON() {
        const json = this._super(...arguments);
        if (this.pos.config.module_pos_hr) {
            json.employee_id = this.cashier ? this.cashier.id : false;
        }
        return json;
    },
});
