import { patch } from "@web/core/utils/patch";
import { fields } from "@mail/model/misc";
import { ResourceResource } from "@resource_mail/core/common/resource_resource_model";

patch(ResourceResource.prototype, {
    setup() {
        super.setup();
        this.employee_id = fields.One("hr.employee");
    },
});
