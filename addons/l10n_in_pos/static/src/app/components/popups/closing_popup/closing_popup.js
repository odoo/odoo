import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { companyStateDialog } from "@l10n_in_pos/app/components/popups/company_state_dialog/company_state_dialog";
import { hsnCodeDialog } from "@l10n_in_pos/app/components/popups/hsn_code_dialog/hsn_code_dialog";

patch(ClosePosPopup.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },

    async confirm() {
        await this.pos.data.read("res.company", [this.pos.company.id]);
        if (this.pos.company.country_id?.code === "IN" && !this.pos.company.state_id) {
            this.dialog.add(companyStateDialog);
            return;
        }

        if (this.pos.company.l10n_in_is_gst_registered) {
            const productIds = await this.orm.call(
                "pos.session",
                "set_missing_hsn_codes_in_pos_orders",
                [this.pos.session.id]
            );
            if (productIds?.length) {
                this.dialog.add(hsnCodeDialog, {
                    productIds: productIds,
                });
                return;
            }
        }
        return await super.confirm();
    },
});
