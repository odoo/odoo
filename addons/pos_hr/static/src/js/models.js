odoo.define('pos_hr.employees', function (require) {
    "use strict";

var { PosGlobalState, Order } = require('point_of_sale.models');
const Registries = require('point_of_sale.Registries');


const PosHrPosGlobalState = (PosGlobalState) => class PosHrPosGlobalState extends PosGlobalState {
    async _processData(loadedData) {
        await super._processData(...arguments);
        if (this.config.module_pos_hr) {
            this.employees = loadedData['hr.employee'];
            this.employee_by_id = loadedData['employee_by_id'];
            this.reset_cashier();
        }
    }
    async after_load_server_data() {
        await super.after_load_server_data(...arguments);
        if (this.config.module_pos_hr) {
            this.hasLoggedIn = !this.config.module_pos_hr;
        }
    }
    reset_cashier() {
        this.cashier = {name: null, id: null, barcode: null, user_id: null, pin: null, role: null};
    }
    set_cashier(employee) {
        this.cashier = employee;
        const selectedOrder = this.get_order();
        if (selectedOrder && !selectedOrder.get_orderlines().length) {
            // Order without lines can be considered to be un-owned by any employee.
            // We set the cashier on that order to the currently set employee.
            selectedOrder.cashier = employee;
        }
        if (!this.cashierHasPriceControlRights() && this.numpadMode === 'price') {
            this.numpadMode = 'quantity';
        }
    }

    /**{name: null, id: null, barcode: null, user_id:null, pin:null}
     * If pos_hr is activated, return {name: string, id: int, barcode: string, pin: string, user_id: int}
     * @returns {null|*}
     */
    get_cashier() {
        if (this.config.module_pos_hr) {
            return this.cashier;
        }
        return super.get_cashier();
    }
    get_cashier_user_id() {
        if (this.config.module_pos_hr) {
            return this.cashier.user_id ? this.cashier.user_id : null;
        }
        return super.get_cashier_user_id();
    }
}
Registries.Model.extend(PosGlobalState, PosHrPosGlobalState);


const PosHrOrder = (Order) => class PosHrOrder extends Order {
    constructor(obj, options) {
        super(...arguments);
        if (!options.json && this.pos.config.module_pos_hr) {
            this.cashier = this.pos.get_cashier();
        }
    }
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        if (this.pos.config.module_pos_hr && json.employee_id) {
            this.cashier = this.pos.employee_by_id[json.employee_id];
        }
    }
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        if (this.pos.config.module_pos_hr) {
            json.employee_id = this.cashier ? this.cashier.id : false;
        }
        return json;
    }
}
Registries.Model.extend(Order, PosHrOrder);

});
