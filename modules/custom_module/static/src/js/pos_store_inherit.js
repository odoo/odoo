/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {

    async showLoginScreen() {
        this.showScreen("FloorScreen");
        this.reset_cashier();
        this.showScreen("LoginScreen");
        this.dialog.closeAll();
    }


});