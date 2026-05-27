import { hrModels } from "@hr/../tests/hr_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class ResUsers extends hrModels.ResUsers {
    leave_date_to = fields.Date({ related: false });

    _store_main_user_fields(res) {
        super._store_main_user_fields(res);
        res.many("all_employee_ids", ["leave_date_to", "on_public_leave"], { internal: true });
    }
}
