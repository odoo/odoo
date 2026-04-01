import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields, makeKwArgs } from "@web/../tests/web_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

export class ResPartner extends mailModels.ResPartner {
    employee_ids = fields.One2many({
        relation: "hr.employee",
        inverse: "work_contact_id",
    });

    _get_store_avatar_card_fields() {
        return [
            ...super._get_store_avatar_card_fields(),
            mailDataHelpers.Store.many(
                "employee_ids",
                makeKwArgs({
                    fields: this.env["hr.employee"]._get_store_avatar_card_fields(),
                    mode: "ADD",
                })
            ),
        ];
    }
}
