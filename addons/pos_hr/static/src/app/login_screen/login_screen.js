/** @odoo-module */

import { useCashierSelector } from "@pos_hr/app/select_cashier_mixin";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component } from "@odoo/owl";

export class LoginScreen extends Component {
    static template = "pos_hr.LoginScreen";
    setup() {
        super.setup(...arguments);
        this.selectCashier = useCashierSelector({
            onCashierChanged: () => this.back(),
            exclusive: true, // takes exclusive control on the barcode reader
        });
        this.pos = usePos();
    }

    back() {
        this.props.resolve({ confirmed: false, payload: false });
        this.pos.closeTempScreen();
        this.pos.hasLoggedIn = true;
        this.pos.openCashControl();
    }

    get shopName() {
        return this.pos.config.name;
    }
}

registry.category("pos_screens").add("LoginScreen", LoginScreen);
