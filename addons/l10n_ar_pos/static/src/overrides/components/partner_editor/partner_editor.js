/** @odoo-module */

import { PartnerDetailsEdit } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import { patch } from "@web/core/utils/patch";

patch(PartnerDetailsEdit.prototype, {
    setup(){
        super.setup(...arguments);
        if (this.pos.isArgentineanCompany()) {
            this.intFields.push("l10n_ar_afip_responsibility_type_id");
            this.intFields.push("l10n_latam_identification_type_id");
            this.changes.l10n_ar_afip_responsibility_type_id =
                this.props.partner.l10n_ar_afip_responsibility_type_id &&
                this.props.partner.l10n_ar_afip_responsibility_type_id[0];
            this.changes.l10n_latam_identification_type_id =
                this.props.partner.l10n_latam_identification_type_id &&
                this.props.partner.l10n_latam_identification_type_id[0];
            }
        },
});
