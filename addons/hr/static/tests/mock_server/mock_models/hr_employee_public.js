import { models } from "@web/../tests/web_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

export class HrEmployeePublic extends models.ServerModel {
    _name = "hr.employee.public";

    _views = {
        search: `<search><field name="display_name" string="Name" /></search>`,
        list: `<list><field name="display_name"/></list>`,
    };

    _get_store_avatar_card_fields() {
        return [
            mailDataHelpers.Store.one(
                "employee_id",
                this.env["hr.employee"]._get_store_avatar_card_fields(...arguments)
            ),
        ];
    }
}
