/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    // @Override
    async processServerData() {
        await super.processServerData();

        if (this.isArgentineanCompany()) {
            this.consumidorFinalAnonimoId = this.data.custom.consumidor_final_anonimo_id;

            this["l10n_latam.identification.type"] =
                this.models["l10n_latam.identification.type"].getAll();
            this["l10n_ar.afip.responsibility.type"] =
                this.models["l10n_ar.afip.responsibility.type"].getAll();
        }
    },
    isArgentineanCompany() {
        return this.company.country_id?.code == "AR";
    },
});

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.pos.isArgentineanCompany()) {
            if (!this.partner) {
                this.partner = this.pos.models["res.partner"].get(
                    this.pos.consumidorFinalAnonimoId
                );
            }
        }
    },
});
