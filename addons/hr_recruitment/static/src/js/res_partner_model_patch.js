import { ResPartner } from "@mail/core/common/res_partner_model";
import { fields } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

patch(ResPartner.prototype, {
    /** @override */
    setup() {
        super.setup(...arguments);
        this.applicant_ids = fields.Many("hr.applicant", { inverse: "partner_id" });
    },
});
