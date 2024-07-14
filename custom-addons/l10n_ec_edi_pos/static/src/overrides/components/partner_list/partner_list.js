/** @odoo-module */

import { PartnerListScreen } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

patch(PartnerListScreen.prototype, {
    createPartner() {
        super.createPartner(...arguments);
        this.state.editModeProps.partner.l10n_latam_identification_type_id = [
            this.pos.l10n_latam_identification_types[0].id,
            this.pos.l10n_latam_identification_types[0].name,
        ];
    },
});
