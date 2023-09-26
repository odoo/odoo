/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    setup(options) {
        super.setup(...arguments);
        // FIXME: options.json is always falsy because json is in the 2nd argument.
        if (!options.json && this.pos.config.module_pos_hr) {
            this.cashier = this.pos.get_cashier();
        }
    },
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        if (this.pos.config.module_pos_hr && json.employee_id) {
            this.cashier = this.pos.employee_by_id[json.employee_id];
        }
    },
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        if (this.pos.config.module_pos_hr) {
            json.employee_id = this.cashier ? this.cashier.id : false;
        }
        return json;
    },
});
