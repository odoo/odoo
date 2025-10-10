import { ResGroups } from "@mail/core/common/model_definitions";
import { fields } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

/** @this {import("models").ResGroups} */
function setup() {
    this.partners = fields.Many("res.partner", { inverse: "group_ids" });
}
patch(ResGroups.prototype, {
    setup() {
        super.setup(...arguments);
        setup.call(this);
    },
});
