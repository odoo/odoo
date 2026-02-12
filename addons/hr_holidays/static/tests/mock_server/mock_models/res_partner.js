import { hrModels } from "@hr/../tests/hr_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

export class ResPartner extends hrModels.ResPartner {
    leave_date_to = fields.Date({ related: false });

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
