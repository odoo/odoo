/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    //@override
    async processServerData() {
        await super.processServerData();
        if (this.company.account_fiscal_country_id.code === "PE") {
            // load the selections to the client
            this.l10n_pe_edi_refund_reason = this.data.custom["l10n_pe_edi_refund_reason"];
        }
    },
});
