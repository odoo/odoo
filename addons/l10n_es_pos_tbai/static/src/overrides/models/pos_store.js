import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async processServerData() {
        await super.processServerData();
        // if (this.company.l10n_es_tbai_is_enabled) {
        //     // load the selections to the client
        //     this.l10n_es_tbai_refund_reason = this.data.custom["l10n_es_tbai_refund_reason"];
        // }
    },
});
