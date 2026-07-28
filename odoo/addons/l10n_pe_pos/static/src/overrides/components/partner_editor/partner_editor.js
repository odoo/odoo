/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { PartnerDetailsEdit } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import { patch } from "@web/core/utils/patch";

patch(PartnerDetailsEdit.prototype, {
    setup() {
        const res = super.setup(...arguments);
        if (!this.pos.isPeruvianCompany()) {
            return res;
        }
        this.intFields.push("city_id", "l10n_latam_identification_type_id", "l10n_pe_district");
        this.changes.city_id = this.props.partner.city_id && this.props.partner.city_id[0];
        this.changes.l10n_latam_identification_type_id =
            this.props.partner.l10n_latam_identification_type_id &&
            this.props.partner.l10n_latam_identification_type_id[0];
        this.changes.l10n_pe_district = this.props.partner.l10n_pe_district && this.props.partner.l10n_pe_district[0];
        return res;
    },
    saveChanges() {
        if (this.pos.isPeruvianCompany() && (!this.props.partner.vat && !this.changes.vat)) {
            return this.popup.add(ErrorPopup, {
                title: _t("Missing Field"),
                body: _t("A Identification Number Is Required"),
            });
        }
        return super.saveChanges(...arguments);
    },
});
