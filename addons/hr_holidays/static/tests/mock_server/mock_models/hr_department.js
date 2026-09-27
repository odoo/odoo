import { fields } from "@web/../tests/web_test_helpers";
import { hrModels } from "@hr/../tests/hr_test_helpers";

export class HrDepartment extends hrModels.HrDepartment {
    _name = "hr.department";

    id = fields.Integer();

    _records = [
        {
            id: 11,
            name: "R&D",
        },
    ];
}
