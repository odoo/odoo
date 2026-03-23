import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { fields, models } from "@web/../tests/web_test_helpers";

export class HrEmployee extends models.ServerModel {
    _name = "hr.employee";

    department_id = fields.Many2one({ relation: "hr.department" });
    name = fields.Char();
    user_id = fields.Many2one({ relation: "res.users" });
    work_email = fields.Char();
    work_phone = fields.Char();
    work_location_type = fields.Char();
    work_location_id = fields.Many2one({ relation: "hr.work.location" });
    job_title = fields.Char();

    _get_store_avatar_card_fields({ add_user = true, ...args } = {}) {
        const res = [
            "company_id",
            mailDataHelpers.Store.one("department_id", ["name"]),
            "hr_icon_display",
            "job_title",
            "name",
            "show_hr_icon_display",
            "work_email",
            mailDataHelpers.Store.one("work_location_id", ["location_type", "name"]),
            "work_phone",
        ];
        if (add_user) {
            res.push(
                mailDataHelpers.Store.one(
                    "user_id",
                    this.env["res.users"]._get_store_avatar_card_fields({
                        ...args,
                        add_employee: false,
                    })
                )
            );
        }
        return res;
    }

    _views = {
        search: `<search><field name="display_name" string="Name" /></search>`,
        list: `<list><field name="display_name"/></list>`,
    };
}
