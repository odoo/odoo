import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useTime } from "@point_of_sale/app/utils/time_hook";
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
        this.selectUser();
    }

    selectUser() {
        this.selectOneCashier(this.pos.user);
    }
    cashierLogIn() {
        const selectedScreen =
            this.pos.previousScreen && this.pos.previousScreen !== "LoginScreen"
                ? this.pos.previousScreen
                : this.pos.firstScreen;
        this.pos.showScreen(selectedScreen);
        this.pos.hasLoggedIn = true;
    }
    selectOneCashier(cashier) {
        this.pos.set_cashier(cashier);
        this.cashierLogIn();
    }
    get backBtnName() {
        return _t("Backend");
    }
    clickBack() {
        this.pos.closePos();
    }
}

registry.category("pos_screens").add("LoginScreen", LoginScreen);
