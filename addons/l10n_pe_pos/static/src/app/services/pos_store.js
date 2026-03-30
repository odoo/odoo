import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    // @Override
    async processServerData() {
        await super.processServerData(...arguments);
        if (this.isPeruvianCompany()) {
            this["res.city"] = this.data["res.city"];
            this["l10n_latam.identification.type"] = this.data["l10n_latam.identification.type"];
            this["l10n_pe.res.city.district"] = this.data["l10n_pe.res.city.district"];
        }
    },
    isPeruvianCompany() {
        return this.company.country_id?.code == "PE";
    },
    getDefaultPartnerId() {
        if (this.isPeruvianCompany()) {
            return this.config._consumidor_final_anonimo_id;
        }
        return super.getDefaultPartnerId();
    },
});
