/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(Navbar.prototype, {
    setup() {
        this.printer = useService("printer");
        super.setup(...arguments);
    },
    onCashMoveButtonClick() {
        this.pos.increaseCashboxOpeningCounter();
        super.onCashMoveButtonClick(...arguments);
    },
    async showLoginScreen() {
        if (this.pos.useBlackBoxBe() && this.pos.checkIfUserClocked()) {
            await this.pos.clock(this.printer, false);
        }
        this.pos.userSessionStatus = await this.pos.getUserSessionStatus();
        super.showLoginScreen();
    },
});
