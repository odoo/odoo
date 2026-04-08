import { fields, models } from "@web/../tests/web_test_helpers";

export class HrWorkEntryType extends models.Model {
    _name = "hr.work.entry.type";

    id = fields.Integer();
    name = fields.Char();

    _records = [
        {
            id: 55,
            name: "Legal Leave",
        },
        {
            id: 65,
            name: "Unpaid Leave",
        },
    ];
}
