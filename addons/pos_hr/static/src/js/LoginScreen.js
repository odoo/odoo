/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";
import { SelectCashierMixin } from "@pos_hr/js/SelectCashierMixin";
import { useBarcodeReader } from "@point_of_sale/js/custom_hooks";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/pos_hook";

export class LoginScreen extends PosComponent {
    static template = "LoginScreen";
}
// FIXME POSREF stop this double patch once the mixin is converted to a hook.
patch(LoginScreen.prototype, "pos_hr.LoginScreen SelectCashierMixin", SelectCashierMixin);
patch(LoginScreen.prototype, "pos_hr.LoginScreen methods", {
    setup() {
        this._super(...arguments);
        useBarcodeReader({ cashier: this.barcodeCashierAction }, true);
        this.pos = usePos();
    },
    async selectCashier() {
        if (await this._super(...arguments)) {
            this.back();
        }
    },
    async barcodeCashierAction(code) {
        if ((await this._super(code)) && this.env.pos.get_cashier().id) {
            this.back();
        }
    },
    back() {
        this.props.resolve({ confirmed: false, payload: false });
        this.pos.closeTempScreen();
        this.env.pos.hasLoggedIn = true;
        this.env.posbus.trigger("start-cash-control");
    },
    confirm() {
        this.props.resolve({ confirmed: true, payload: true });
        this.pos.closeTempScreen();
    },
    get shopName() {
        return this.env.pos.config.name;
    },
});

registry.category("pos_screens").add("LoginScreen", LoginScreen);
