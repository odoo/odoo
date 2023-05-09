/** @odoo-module */

import { useCashierSelector } from "@pos_hr/js/SelectCashierMixin";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/pos_hook";
import { Component } from "@odoo/owl";

export class LoginScreen extends Component {
    static template = "LoginScreen";
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
        this.pos.globalState.hasLoggedIn = true;
        this.pos.openCashControl();
    }

    get shopName() {
        return this.pos.globalState.config.name;
    }
}

registry.category("pos_screens").add("LoginScreen", LoginScreen);
