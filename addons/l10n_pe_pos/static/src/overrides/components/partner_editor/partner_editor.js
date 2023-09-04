/** @odoo-module **/

import PartnerDetailsEdit from "point_of_sale.PartnerDetailsEdit";
import {patch} from "@web/core/utils/patch";

patch(PartnerDetailsEdit.prototype, "l10n_pe_pos.PartnerDetailsEdit", {
    setup() {
        this._super(...arguments);
        if (this.env.pos.isPeruvianCompany()) {
            this.intFields.push("l10n_latam_identification_type_id");
            this.changes.l10n_latam_identification_type_id =
                this.props.partner.l10n_latam_identification_type_id &&
                this.props.partner.l10n_latam_identification_type_id[0];
        }
    },
});
