/** @odoo-module */

import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

patch(PartnerList.prototype, {
    newPartnerDefaults() {
        const newPartner = super.newPartnerDefaults(...arguments);
        if (this.pos.isArgentineanCompany()) {
            newPartner.l10n_latam_identification_type_id = this.pos.models[
                "l10n_latam.identification.type"
            ].get(this.pos["l10n_latam.identification.type"][0].id);

            newPartner.l10n_ar_afip_responsibility_type_id = this.pos.models[
                "l10n_ar.afip.responsibility.type"
            ].get(this.pos["l10n_ar.afip.responsibility.type"][0].id);
        }
        return newPartner;
    },
});
