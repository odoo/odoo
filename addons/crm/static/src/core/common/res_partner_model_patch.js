import { ResPartner } from "@mail/core/common/res_partner_model";
import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

patch(ResPartner.prototype, {
    setup() {
        super.setup();
        this.opportunity_ids = fields.Many("crm.lead");
    },
});
