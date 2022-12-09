/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";
import SelectCashierMixin from "@pos_hr/js/SelectCashierMixin";
import { useBarcodeReader } from "@point_of_sale/js/custom_hooks";

class LoginScreen extends SelectCashierMixin(PosComponent) {
    setup() {
        super.setup();
        useBarcodeReader({ cashier: this.barcodeCashierAction }, true);
    }
    async selectCashier() {
        if (await super.selectCashier()) {
            this.back();
        }
    }
    async barcodeCashierAction(code) {
        if (await super.barcodeCashierAction(code)) {
            this.back();
        }
    }
    back() {
        this.props.resolve({ confirmed: false, payload: false });
        this.trigger("close-temp-screen");
        this.env.pos.hasLoggedIn = true;
        this.env.posbus.trigger("start-cash-control");
    }
    confirm() {
        this.props.resolve({ confirmed: true, payload: true });
        this.trigger("close-temp-screen");
    }
    get shopName() {
        return this.env.pos.config.name;
    }
}
LoginScreen.template = "LoginScreen";

Registries.Component.add(LoginScreen);

export default LoginScreen;
