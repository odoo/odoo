/** @odoo-module */

import { Chrome } from "@point_of_sale/js/Chrome";
import { patch } from "@web/core/utils/patch";

patch(Chrome.prototype, "pos_hr.Chrome", {
    async start() {
        await this._super(...arguments);
        if (this.env.pos.config.module_pos_hr) {
            this.pos.showTempScreen("LoginScreen"); // FIXME POSREF: use startScreen instead.
        }
    },
    get showCashMoveButton() {
        return (
            this._super(...arguments) &&
            (!this.env.pos.cashier || this.env.pos.cashier.role == "manager")
        );
    },
});
