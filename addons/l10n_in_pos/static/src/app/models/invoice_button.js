import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";

import { patch } from "@web/core/utils/patch";
import { companyStateDialog } from "@l10n_in_pos/app/components/popups/company_state_dialog/company_state_dialog";

patch(InvoiceButton.prototype, {
    async click() {
        await this.pos.data.read("res.company", [this.pos.company.id]);
        if (this.pos.company.country_id?.code === "IN" && !this.pos.company.state_id) {
            this.dialog.add(companyStateDialog);
            return;
        }
        return await super.click();
    },
});
