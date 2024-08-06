import { models } from "@web/../tests/web_test_helpers";

export class HrEmployee extends models.ServerModel {
    _name = "hr.employee";

    _views = {
        search: `<search><field name="display_name" string="Name" /></search>`,
        list: `<tree><field name="display_name"/></tree>`,
    };
}
