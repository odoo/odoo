/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    get showCashMoveButton() {
        if (!this.pos.config.module_pos_hr) {
            return super.showCashMoveButton;
        }

        const { cashier } = this.pos;
        const security = this.pos.employee_security[cashier.id];
        return super.showCashMoveButton && (!cashier || security.role == "manager");
    },
    employeeIsAdmin() {
        if (!this.pos.config.module_pos_hr) {
            return super.employeeIsAdmin();
        }

        const cashier = this.pos.get_cashier();
        const security = this.pos.employee_security[cashier.id];
        return security.role === "manager" || cashier.user_id?.id === this.pos.user.id;
    },
    async showLoginScreen() {
        this.pos.reset_cashier();
        this.pos.showScreen("LoginScreen");
    },
});
