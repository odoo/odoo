import { HrEmployeePublic } from "@hr/../tests/mock_server/mock_models/hr_employee_public";

import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
import { patch } from "@web/core/utils/patch";

patch(HrEmployeePublic.prototype, {
    _get_store_avatar_card_fields() {
        return [
            ...super._get_store_avatar_card_fields(),
            mailDataHelpers.Store.many("employee_skill_ids", ["color", "display_name"]),
        ];
    },
});
