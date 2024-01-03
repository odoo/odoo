/** @odoo-module */

import { useCashierSelector } from "@pos_hr/app/select_cashier_mixin";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component } from "@odoo/owl";

export class LoginScreen extends Component {
    static template = "pos_hr.LoginScreen";
    static storeOnOrder = false;
    setup() {
<<<<<<< HEAD
        this.pos = usePos();
        this.selectCashier = useCashierSelector({
            onCashierChanged: () => {
                this.pos.showScreen(this.pos.previousScreen || "ProductScreen");
                this.pos.hasLoggedIn = true;
            },
||||||| parent of 79351a23bdf8 (temp)
        super.setup(...arguments);
        this.selectCashier = useCashierSelector({
            onCashierChanged: () => this.back(),
=======
        super.setup(...arguments);
        this.cashierSelector = useCashierSelector({
            onCashierChanged: () => this.back(),
>>>>>>> 79351a23bdf8 (temp)
            exclusive: true, // takes exclusive control on the barcode reader
        });
    }

    async selectCashier() {
        return await this.cashierSelector();
    }
}
registry.category("pos_screens").add("LoginScreen", LoginScreen);
