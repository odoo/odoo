import { ResPartner } from "@mail/core/common/res_partner_model";
import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

patch(ResPartner.prototype, {
    /** @type {number|undefined} */
    employeeId: undefined,
    setup() {
        super.setup();
        this.employee_ids = fields.Many("hr.employee", {
            inverse: "work_contact_id",
        });
        this.employee_id = fields.One("hr.employee", {
            compute() {
                return (
                    this.employee_ids.find(
                        (employee) => employee.company_id?.id === user.activeCompany.id
                    ) || this.employee_ids[0]
                );
            },
        });
    },
});
