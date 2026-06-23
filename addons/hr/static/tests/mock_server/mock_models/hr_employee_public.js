import { models } from "@web/../tests/web_test_helpers";

export class HrEmployeePublic extends models.ServerModel {
    _name = "hr.employee.public";

    _views = {
        search: `<search><field name="display_name" string="Name" /></search>`,
        list: `<list><field name="display_name"/></list>`,
    };

    _store_avatar_card_fields(res) {
        res.one("employee_id", "_store_avatar_card_fields", { sudo: true });
    }
}
