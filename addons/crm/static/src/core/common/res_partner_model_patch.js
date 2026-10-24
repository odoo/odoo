import { ResPartner } from "@mail/core/common/res_partner_model";
import { fields, patchModel } from "@mail/model/export";

export const resPartnerPatch = patchModel(ResPartner, {
    setup() {
        super.setup();
        this.opportunity_ids = fields.Many("crm.lead");
    },
});
