/** @odoo-module */

import { CashMovePopup } from "@point_of_sale/app/navbar/cash_move_popup/cash_move_popup";

import { patch } from "@web/core/utils/patch";
import { companyStateDialog } from "@l10n_in_pos/company_state_dialog/company_state_dialog";

patch(CashMovePopup.prototype, {
    async confirm() {
        if (this.pos.company.country_id?.code === "IN" && !this.pos.company.state_id) {
            this.dialog.add(companyStateDialog);
            return;
        }
        return await super.confirm();
    },
});
