import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class ResPartner extends mailModels.ResPartner {
    out_of_office_date_end = fields.Date();

    /**
     * Overrides to add out of office to employees.
     * @override
     * @type {typeof mailModels.ResPartner["prototype"]["mail_partner_format"]}
     */
    mail_partner_format(ids) {
        const partnerFormats = super.mail_partner_format(...arguments);
        const partners = this._filter([["id", "in", ids]], {
            active_test: false,
        });
        for (const partner of partners) {
            // Not a real field but ease the testing
            partnerFormats[partner.id].out_of_office_date_end = partner.out_of_office_date_end;
        }
        return partnerFormats;
    }
}
