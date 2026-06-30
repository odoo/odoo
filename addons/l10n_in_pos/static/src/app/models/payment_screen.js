import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

import { patch } from "@web/core/utils/patch";
import { companyStateDialog } from "@l10n_in_pos/app/components/popups/company_state_dialog/company_state_dialog";

patch(PaymentScreen.prototype, {
    async toggleIsToInvoice() {
        await this.pos.data.read("res.company", [this.pos.company.id]);
        if (this.pos.company.country_id?.code === "IN" && !this.pos.company.state_id) {
            this.dialog.add(companyStateDialog);
            return;
        }
        return await super.toggleIsToInvoice();
    },
});
