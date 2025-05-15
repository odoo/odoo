/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(Navbar.prototype, {

    setup() {
        console.log('okayyyyyyyy');
        super.setup();
        this.pos = usePos();
    },
    async showLoginScreen() {
        console.log('here');
        this.pos.showScreen("FloorScreen");
        this.pos.reset_cashier();
        await this.pos.showTempScreen("LoginScreen");
    },
});
