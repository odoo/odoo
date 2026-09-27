import { ResPartner } from "@mail/core/common/res_partner_model";
import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";

patch(ResPartner.prototype, {
    setup() {
        super.setup();
        /** @type {number|undefined} */
        this.employeeId = undefined;
        this.employee_ids = fields.Many("hr.employee", {
            inverse: "work_contact_id",
        });
        this.employee_id = this.computed(() => this.store.getRelevantEmployee(this.employee_ids));
    },
});
