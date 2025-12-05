import { fields, models } from "@web/../tests/web_test_helpers";

export class HrEmployee extends models.ServerModel {
    _name = "hr.employee";

    department_id = fields.Many2one({ relation: "hr.department" });
    work_email = fields.Char();
    work_phone = fields.Char();
    work_location_type = fields.Char();
    work_location_id = fields.Many2one({ relation: "hr.work.location" });
    job_title = fields.Char();

    _get_store_avatar_card_fields() {
        return this.env["hr.employee.public"]._get_store_avatar_card_fields();
    }

    _views = {
        search: `<search><field name="display_name" string="Name" /></search>`,
        list: `<list><field name="display_name"/></list>`,
    };
}
