import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class ResUsers extends mailModels.ResUsers {
    work_email = fields.Char();
    work_phone = fields.Char();
    job_title = fields.Char();
    department_id = fields.Many2one({ relation: "hr.department" });
}
