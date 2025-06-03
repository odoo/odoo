import { ResPartner } from "@mail/core/common/res_partner_model";
import { fields } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

patch(ResPartner.prototype, {
    setup() {
        super.setup();
        this.opportunity_ids = fields.Many("crm.lead");
    },
});
