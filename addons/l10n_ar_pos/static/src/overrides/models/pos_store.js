import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    // @Override
    async processServerData() {
        await super.processServerData();

        if (this.isArgentineanCompany()) {
            this["l10n_latam.identification.type"] =
                this.models["l10n_latam.identification.type"].getFirst();
            this["l10n_ar.afip.responsibility.type"] =
                this.models["l10n_ar.afip.responsibility.type"].getFirst();
        }
    },
    isArgentineanCompany() {
        return this.company.country_id?.code == "AR";
    },
});
