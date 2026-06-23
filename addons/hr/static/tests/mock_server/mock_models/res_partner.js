import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class ResPartner extends mailModels.ResPartner {
    employee_ids = fields.One2many({
        relation: "hr.employee",
        inverse: "work_contact_id",
    });

    _store_avatar_card_fields(res) {
        super._store_avatar_card_fields(res);
        if (res.is_for_internal_users()) {
            res.many("employee_ids", "_store_avatar_card_fields", { sudo: true });
        }
    }
}
