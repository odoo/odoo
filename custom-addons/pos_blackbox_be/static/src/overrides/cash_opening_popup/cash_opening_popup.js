/** @odoo-module */

import { CashOpeningPopup } from "@point_of_sale/app/store/cash_opening_popup/cash_opening_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(CashOpeningPopup.prototype, {
    setup() {
        super.setup();
        this.printer = useService("printer");
    },
    async confirm() {
        await super.confirm();
        if (this.pos.useBlackBoxBe() && !this.pos.checkIfUserClocked()) {
            await this.pos.clock(this.printer, true);
        }
        this.pos.userSessionStatus = await this.pos.getUserSessionStatus();
    },
});
