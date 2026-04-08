import { HrEmployeePublic } from "@hr/../tests/mock_server/mock_models/hr_employee_public";

import { patch } from "@web/core/utils/patch";

patch(HrEmployeePublic.prototype, {
    _get_store_avatar_card_fields() {
        return [...super._get_store_avatar_card_fields(), "leave_date_to"];
    },
});
