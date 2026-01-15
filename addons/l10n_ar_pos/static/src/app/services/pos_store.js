import { PosStore } from "@point_of_sale/app/services/pos_store";
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
    createNewOrder() {
        const order = super.createNewOrder(...arguments);

        if (this.isArgentineanCompany() && !order.partner_id) {
            order.partner_id = this.config._consumidor_final_anonimo_id;
        }

        return order;
    },
});
