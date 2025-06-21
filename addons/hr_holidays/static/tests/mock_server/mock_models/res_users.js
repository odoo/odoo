import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class ResUsers extends mailModels.ResUsers {
    employee_id = fields.Many2one({ relation: "hr.employee" });
    employee_ids = fields.One2many({
        relation: "hr.employee",
        inverse: "user_id",
    });
    leave_date_to = fields.Date({ related: false });

    _get_store_avatar_card_related_fields() {
        return {
            employee_ids: ["leave_date_to"],
        };
    }
    _get_store_avatar_card_fields() {
        const fields = super._get_store_avatar_card_fields();
        return fields.concat(["employee_ids"]);
    }
}
