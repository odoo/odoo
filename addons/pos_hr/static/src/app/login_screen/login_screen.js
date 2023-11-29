/** @odoo-module */

import { useCashierSelector } from "@pos_hr/app/select_cashier_mixin";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component } from "@odoo/owl";

export class LoginScreen extends Component {
    static template = "pos_hr.LoginScreen";
    static props = {};
    static storeOnOrder = false;
    setup() {
        this.pos = usePos();
        this.selectCashier = useCashierSelector({
            onCashierChanged: () => {
                this.pos.showScreen(this.pos.previousScreen || "ProductScreen");
                this.pos.hasLoggedIn = true;
            },
            exclusive: true, // takes exclusive control on the barcode reader
        });
    }
}
registry.category("pos_screens").add("LoginScreen", LoginScreen);
