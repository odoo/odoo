/** @odoo-module **/

import PartnerListScreen from "point_of_sale.PartnerListScreen";
import {patch} from "@web/core/utils/patch";

patch(PartnerListScreen.prototype, "l10n_pe_pos.PartnerListScreen", {
    createPartner() {
        this._super(...arguments);
        if (this.env.pos.isPeruvianCompany()) {
            this.state.editModeProps.partner.l10n_latam_identification_type_id = [
                this.env.pos.l10n_latam_identification_types[0].id,
                this.env.pos.l10n_latam_identification_types[0].name,
            ];
        }
    },
});
