/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    get showCashMoveButton() {
        if (!this.pos.config.module_pos_hr) {
            return super.showCashMoveButton;
        }

        const { cashier } = this.pos;
        return super.showCashMoveButton && (!cashier || cashier._role == "manager");
    },
    employeeIsAdmin() {
        if (!this.pos.config.module_pos_hr) {
            return super.employeeIsAdmin();
        }

        const cashier = this.pos.get_cashier();
        return cashier._role === "manager" || cashier.user_id?.id === this.pos.user.id;
    },
    async showLoginScreen() {
        this.pos.reset_cashier();
        this.pos.showScreen("LoginScreen");
    },
});
