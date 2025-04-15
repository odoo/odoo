/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    // @Override
    async _processData(loadedData) {
        await super._processData(...arguments);
        if (this.isArgentineanCompany()) {
            this.l10n_ar_afip_responsibility_types = loadedData["l10n_ar.afip.responsibility.type"];
            this.l10n_latam_identification_types = loadedData["l10n_latam.identification.type"];
            this.consumidorFinalAnonimoId = loadedData["consumidor_final_anonimo_id"];
        }
    },
    isArgentineanCompany() {
        return this.company.country?.code == "AR";
    },
});

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.pos.isArgentineanCompany()) {
            if (!this.partner) {
                this.partner = this.pos.db.partner_by_id[this.pos.consumidorFinalAnonimoId];
            }
        }
    },
});
