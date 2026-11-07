/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    get showCashMoveButton() {
        const { cashier } = this.pos;
        return super.showCashMoveButton && (!cashier || cashier.role == "manager");
    },
    get showCloseSessionButton() {
        return (
            !this.pos.config.module_pos_hr ||
            (this.pos.get_cashier().role === "manager" && this.pos.get_cashier().user_id) ||
            this.pos.get_cashier_user_id() === this.pos.user.id
        );
    },
    get showBackendButton() {
        return (
            !this.pos.config.module_pos_hr ||
            (this.pos.get_cashier().role === "manager" && this.pos.get_cashier().user_id) ||
            this.pos.get_cashier_user_id() === this.pos.user.id
        );
    },
    async showLoginScreen() {
        this.pos.reset_cashier();
        await this.pos.showTempScreen("LoginScreen");
    },
});
