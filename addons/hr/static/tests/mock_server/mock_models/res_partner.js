import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

export class ResPartner extends mailModels.ResPartner {
    employee_ids = fields.One2many({
        relation: "hr.employee",
        inverse: "work_contact_id",
    });

    _get_store_avatar_card_fields({ add_empoyee = true, ...args } = {}) {
        const res = super._get_store_avatar_card_fields(...arguments);
        if (add_empoyee) {
            res.push(
                mailDataHelpers.Store.many(
                    "employee_ids",
                    this.env["hr.employee"]._get_store_avatar_card_fields({
                        ...args,
                        add_partner: false,
                    })
                )
            );
        }
        return res;
    }
}
