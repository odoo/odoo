import { patch } from "@web/core/utils/patch";
import { fields } from "@mail/model/misc";
import { ResourceResource } from "@resource_mail/core/common/resource_resource_model";

patch(ResourceResource.prototype, {
    setup() {
        super.setup();
        /** ⚠️ This field is named like a One but it is actually a Many. */
        this.employee_id = fields.Many("hr.employee", { inverse: "resource_id" });
    },
});
