import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

patch(mailModels.ResUsers.prototype, {
    setup() {
        super.setup(...arguments);
        this.employee_id = fields.Many2one({ relation: "hr.employee" });
        this.employee_ids = fields.One2many({
            relation: "hr.employee",
            inverse: "user_id",
        });
        this.department_id = fields.Many2one({
            related: "employee_id.department_id",
            relation: "hr.department",
        });
        this.work_email = fields.Char({ related: "employee_id.work_email" });
        this.work_phone = fields.Char({ related: "employee_id.work_phone" });
        this.work_location_type = fields.Char({ related: "employee_id.work_location_type" });
        this.work_location_id = fields.Many2one({
            related: "employee_id.work_location_id",
            relation: "hr.work.location",
        });
        this.job_title = fields.Char({ related: "employee_id.job_title" });
    },
});
