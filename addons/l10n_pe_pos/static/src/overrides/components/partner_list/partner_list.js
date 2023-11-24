/** @odoo-module */

import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

patch(PartnerList.prototype, {
    createPartner() {
        const res = super.createPartner(...arguments);
        if (!this.pos.isPeruvianCompany()) {
            return res;
        }
        this.props.partner.city_id = this.pos.models["res.city"].get(this.pos["res.city"][0].id);
        this.props.partner.l10n_latam_identification_type_id = this.pos.models[
            "l10n_latam.identification.type"
        ].get(this.pos["l10n_latam.identification.type"][0].id);
        this.props.partner.l10n_pe_district = this.pos.models[
            "l10n_pe.res.city.district"
        ].get(this.pos["l10n_pe.res.city.district"][0].id);
        return res;
    },
});
