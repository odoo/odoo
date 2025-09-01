import { hrModels } from "@hr/../tests/hr_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

export class ResPartner extends hrModels.ResPartner {
    leave_date_to = fields.Date({ related: false });

    compute_im_status(partner) {
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];
        if (partner.main_user_id && ResUsers.browse(partner.main_user_id).leave_date_to) {
            if (partner.im_status === "online") {
                return "leave_online";
            } else if (partner.im_status === "away") {
                return "leave_away";
            } else {
                return "leave_offline";
            }
        } else {
            return super.compute_im_status(partner);
        }
    }

    get _to_store_defaults() {
        return [
            ...super._to_store_defaults,
            mailDataHelpers.Store.one(
                "main_user_id",
                mailDataHelpers.Store.many("employee_ids", "leave_date_to")
            ),
        ];
    }
}
