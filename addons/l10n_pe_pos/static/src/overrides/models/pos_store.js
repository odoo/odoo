/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    // @Override
    async processServerData() {
        await super.processServerData(...arguments);
        if (this.isPeruvianCompany()) {
            this["res.city"] = this.models["res.city"].getAll();
            this.consumidorFinalAnonimoId = this.data.custom["consumidor_final_anonimo_id"];
            this.default_l10n_latam_identification_type_id =
                this.data.custom["default_l10n_latam_identification_type_id"];
            this["l10n_latam.identification.type"] =
                this.models["l10n_latam.identification.type"].getAll();
            this["l10n_pe.res.city.district"] = this.models["l10n_pe.res.city.district"].getAll();
        }
    },
    isPeruvianCompany() {
        return this.company.country_id?.code == "PE";
    },
});
