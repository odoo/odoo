import { HrEmployee } from "@hr/../tests/mock_server/mock_models/hr_employee";

import { patch } from "@web/core/utils/patch";

patch(HrEmployee.prototype, {
    _store_avatar_card_fields(res) {
        super._store_avatar_card_fields(res);
        res.many("employee_skill_ids", ["color", "display_name"]);
    },
});
