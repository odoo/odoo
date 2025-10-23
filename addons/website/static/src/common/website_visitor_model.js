import { WebsiteVisitor } from "@mail/core/common/model_definitions";
import { fields } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

patch(WebsiteVisitor.prototype, {
    setup() {
        super.setup(...arguments);
        this.country = fields.One("res.country", {
            /** @this {import("models").WebsiteVisitor} */
            compute() {
                return this.partner_id?.country_id || this.country_id;
            },
        });
    },
});
export { WebsiteVisitor };
