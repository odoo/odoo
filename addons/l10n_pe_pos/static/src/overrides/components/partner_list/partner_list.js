/** @odoo-module */

import { PartnerListScreen } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

patch(PartnerListScreen.prototype, {
    createPartner() {
        const res = super.createPartner(...arguments);
        if (!this.pos.isPeruvianCompany()) {
            return res;
        }
        this.state.editModeProps.partner.city_id = [this.pos.cities[0].id, this.pos.cities[0].name];
        this.state.editModeProps.partner.l10n_latam_identification_type_id = [
            this.pos.l10n_latam_identification_types[0].id,
            this.pos.l10n_latam_identification_types[0].name,
        ];
        this.state.editModeProps.partner.l10n_pe_district = [
            this.pos.l10n_pe_districts[0].id,
            this.pos.l10n_pe_districts[0].name,
        ];
        return res;
    },
});
