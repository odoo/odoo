import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";

import { patch } from "@web/core/utils/patch";
import { companyStateDialog } from "@l10n_in_pos/app/components/popups/company_state_dialog/company_state_dialog";

patch(ClosePosPopup.prototype, {
    async confirm() {
        await this.pos.data.read("res.company", [this.pos.company.id]);
        if (this.pos.company.country_id?.code === "IN" && !this.pos.company.state_id) {
            this.dialog.add(companyStateDialog);
            return;
        }
        return await super.confirm();
    },
});
