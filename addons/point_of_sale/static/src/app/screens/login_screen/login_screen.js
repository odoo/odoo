import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useTime } from "@point_of_sale/app/hooks/time_hook";
import { _t } from "@web/core/l10n/translation";

export class LoginScreen extends Component {
    static template = "point_of_sale.LoginScreen";
    static props = {};
    static storeOnOrder = false;
    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.ui = useState(useService("ui"));
        this.time = useTime();
    }

    openRegister() {
        this.pos.setSessionCashierInfo({ userId: this.pos.user.id });
        this.cashierLogIn();
    }
    cashierLogIn() {
        this.pos.cashier.logged = true;
        const selectedScreen =
            this.pos.previousScreen && this.pos.previousScreen !== "LoginScreen"
                ? this.pos.previousScreen
                : this.pos.firstScreen;
        this.pos.showScreen(selectedScreen);
    }
    get backBtnName() {
        return _t("Backend");
    }
    clickBack() {
        this.pos.closePos();
    }
}

registry.category("pos_screens").add("LoginScreen", LoginScreen);
