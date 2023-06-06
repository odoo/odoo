/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, "pos_hr.Navbar", {
    get showCashMoveButton() {
        const { cashier } = this.pos.globalState;
        return this._super(...arguments) && (!cashier || cashier.role == "manager");
    },
    get showCloseSessionButton() {
        return (
            !this.pos.globalState.config.module_pos_hr ||
            (this.pos.globalState.get_cashier().role === "manager" &&
                this.pos.globalState.get_cashier().user_id) ||
            this.pos.globalState.get_cashier_user_id() === this.pos.globalState.user.id
        );
    },
    get showBackendButton() {
        return (
            !this.pos.globalState.config.module_pos_hr ||
            (this.pos.globalState.get_cashier().role === "manager" &&
                this.pos.globalState.get_cashier().user_id) ||
            this.pos.globalState.get_cashier_user_id() === this.pos.globalState.user.id
        );
    },
    async showLoginScreen() {
        this.pos.globalState.reset_cashier();
        await this.pos.showTempScreen("LoginScreen");
    },
});
