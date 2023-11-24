/** @odoo-module */

import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
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
    /**
     * Now, vat is required by Peruvian Localization and it is important to display errors during partners creation,
     * mainly, if they are related to the format of the vat
     * https://github.com/odoo/odoo/blob/6e8e3e63/addons/base_vat/models/res_partner.py#L267
     */
    async saveChanges(processedChanges) {
        let partnerId;
        try {
            partnerId = await this.orm.call("res.partner", "create_from_ui", [processedChanges]);
        } catch (error) {
            return this.env.services.popup.add(ErrorPopup, {
                title: error.message,
                body: error.data.message,
            });
        }
        if (partnerId) {
            processedChanges.id = partnerId;
        }
        await super.saveChanges(...arguments);
    },
});
