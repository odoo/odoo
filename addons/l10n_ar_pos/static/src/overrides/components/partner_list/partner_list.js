/** @odoo-module */

import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

patch(PartnerList.prototype, {
    createPartner() {
        super.createPartner(...arguments);
        if (this.pos.isArgentineanCompany()) {
            this.props.partner.l10n_latam_identification_type_id = this.pos.models[
                "l10n_latam.identification.type"
            ].get(this.pos["l10n_latam.identification.type"][0].id);

            this.props.partner.l10n_ar_afip_responsibility_type_id = this.pos.models[
                "l10n_ar.afip.responsibility.type"
            ].get(this.pos["l10n_ar.afip.responsibility.type"][0].id);
        }
    },
});
