/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PartnerEditor } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import { patch } from "@web/core/utils/patch";

patch(PartnerEditor.prototype, {
    setup() {
        const res = super.setup(...arguments);
        if (!this.pos.isPeruvianCompany()) {
            return res;
        }
        this.intFields.push("city_id", "l10n_latam_identification_type_id", "l10n_pe_district");
        this.changes.city_id = this.props.partner.city_id && this.props.partner.city_id.id;
        this.changes.l10n_latam_identification_type_id =
            this.props.partner.l10n_latam_identification_type_id &&
            this.props.partner.l10n_latam_identification_type_id.id ||
            this.pos.default_l10n_latam_identification_type_id;
        this.changes.l10n_pe_district = this.props.partner.l10n_pe_district && this.props.partner.l10n_pe_district.id;
        return res;
    },
    async confirm() {
        if (!this.pos.isPeruvianCompany()) {
            return await super.confirm(...arguments);
        }
        const city = this.pos.models["res.city"].find((city) => city.id === parseInt(this.changes.city_id));
        const district = this.pos.models["l10n_pe.res.city.district"].find((district) => district.id === parseInt(this.changes.l10n_pe_district));
        if (!city || (parseInt(this.changes.state_id) !== city.state_id.id || parseInt(this.changes.country_id) !== city.country_id.id)) {
            this.changes.city_id = '';
        }
        
        if (!district || parseInt(this.changes.city_id) !== district.city_id.id) {
            this.changes.l10n_pe_district = '';
        }
        if (!this.changes.vat) {
            return this.dialog.add(AlertDialog, {
                title: _t("Missing Field"),
                body: _t("An Identification Number Is Required"),
            });
        }
        return await super.confirm(...arguments);
    },
});
