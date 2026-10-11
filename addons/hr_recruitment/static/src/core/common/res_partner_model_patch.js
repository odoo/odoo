import { ResPartner } from "@mail/core/common/res_partner_model";
import { fields, patchModel } from "@mail/model/export";

export const resPartnerPatch = patchModel(ResPartner, {
    /** @override */
    setup() {
        super.setup(...arguments);
        this.applicant_ids = fields.Many("hr.applicant", { inverse: "partner_id" });
    },
});
