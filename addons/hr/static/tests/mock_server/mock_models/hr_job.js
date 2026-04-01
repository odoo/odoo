import { models } from "@web/../tests/web_test_helpers";

export class HrJob extends models.ServerModel {
    _name = "hr.job";

    _views = {
        search: `<search><field name="display_name" string="Name" /></search>`,
        list: `<list><field name="display_name"/></list>`,
    };
}
