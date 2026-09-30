import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class ResUsers extends mailModels.ResUsers {
    employee_id = fields.Many2one({ relation: "hr.employee" });
    employee_ids = fields.One2many({
        relation: "hr.employee",
        inverse: "user_id",
    });
    department_id = fields.Many2one({
        related: "employee_id.department_id",
        relation: "hr.department",
    });
    work_email = fields.Char({ related: "employee_id.work_email" });
    work_phone = fields.Char({ related: "employee_id.work_phone" });
    work_location_type = fields.Char({ related: "employee_id.work_location_type" });
    work_location_id = fields.Many2one({
        related: "employee_id.work_location_id",
        relation: "hr.work.location",
    });
    job_title = fields.Char({ related: "employee_id.job_title" });
}
