import { hrModels } from "@hr/../tests/hr_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class HrEmployee extends hrModels.HrEmployee {
    _name = "hr.employee";

    leave_date_to = fields.Date();

    _records = [
        {
            id: 100,
            name: "Richard",
            department_id: 11,
            company_id: 1,
        },
        {
            id: 200,
            name: "Jane",
            department_id: 11,
        },
    ];

    _store_avatar_card_fields(res) {
        super._store_avatar_card_fields(res);
        res.attr("leave_date_to");
    }

    _store_im_status_fields(res) {
        super._store_im_status_fields(res);
        res.attr("leave_date_to");
    }
}
