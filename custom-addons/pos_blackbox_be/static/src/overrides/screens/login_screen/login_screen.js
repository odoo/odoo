/** @odoo-module **/

import { LoginScreen } from "@pos_hr/app/login_screen/login_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(LoginScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.printer = useService("printer");
    },
    async selectCashier() {
        const result = await super.selectCashier();
        if (
            !this.pos.shouldShowCashControl() &&
            this.pos.useBlackBoxBe() &&
            !this.pos.checkIfUserClocked()
        ) {
            await this.pos.clock(this.printer, true);
        }
        this.pos.userSessionStatus = await this.pos.getUserSessionStatus();
        return result;
    },
});
