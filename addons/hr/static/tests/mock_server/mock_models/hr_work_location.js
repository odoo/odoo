import { models, fields } from "@web/../tests/web_test_helpers";

export class HrWorkLocation extends models.ServerModel {
    _name = "hr.work.location";

    name = fields.Char();
    location_type = fields.Selection({
        selection: [
            ["office", "Office"],
            ["home", "Home"],
            ["other", "Other"],
        ],
    });

    _views = {
        search: `<search><field name="display_name" string="Name" /></search>`,
        list: `<list><field name="display_name"/></list>`,
    };
}
