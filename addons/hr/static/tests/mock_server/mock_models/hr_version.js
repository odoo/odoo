import { fields, models } from "@web/../tests/web_test_helpers";

export class HrVersion extends models.ServerModel {
    _name = "hr.version";

    date_version = fields.Date();
    display_name = fields.Char();
    employee_id = fields.Many2one({ relation: "hr.employee" });

    _views = {
        search: `<search><field name="display_name" string="Name" /></search>`,
        list: `<list><field name="display_name"/></list>`,
    };
}
