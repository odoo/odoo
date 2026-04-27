/** @odoo-module **/

import { LoginScreen } from "@point_of_sale/app/screens/login_screen/login_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(LoginScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.printer = useService("printer");
    },
    async selectCashier(pin = false, login = false, list = false) {
        const result = await super.selectCashier(...arguments);
        if (
            result &&
            !this.pos.shouldShowOpeningControl() &&
            this.pos.useBlackBoxBe() &&
            !this.pos.checkIfUserClocked() &&
            this.pos.mainScreen.component != LoginScreen
        ) {
            await this.pos.clock(this.printer, true);
        }
        this.pos.user_session_status = await this.pos.getUserSessionStatus();
        return result;
    },
});
