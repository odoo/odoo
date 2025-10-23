import { ResGroups } from "@mail/core/common/model_definitions";
import { fields } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

patch(ResGroups.prototype, {
    setup() {
        super.setup(...arguments);
        this.partners = fields.Many("res.partner", { inverse: "group_ids" });
    },
});
