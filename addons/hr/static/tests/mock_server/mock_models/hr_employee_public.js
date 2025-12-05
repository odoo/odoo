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
            "company_id",
            mailDataHelpers.Store.one("department_id", ["name"]),
            "hr_icon_display",
            "name",
            "job_title",
            "show_hr_icon_display",
            mailDataHelpers.Store.one("user_id", [
                "share",
                mailDataHelpers.Store.one("partner_id", "im_status"),
            ]),
            "work_email",
            mailDataHelpers.Store.one("work_location_id", ["location_type", "name"]),
            "work_phone",
        ];
    }
}
