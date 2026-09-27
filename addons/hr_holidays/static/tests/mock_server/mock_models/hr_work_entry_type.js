import { fields, models } from "@web/../tests/web_test_helpers";

export class HrWorkEntryType extends models.Model {
    _name = "hr.work.entry.type";

    id = fields.Integer();
    name = fields.Char();
    color = fields.Integer();
    display_name = fields.Char();

    _records = [
        {
            id: 55,
            name: "Legal Leave",
            display_name: "Legal Leave",
            color: 1,
        },
        {
            id: 65,
            name: "Unpaid Leave",
            display_name: "Unpaid Leave",
            color: 5,
        },
    ];
}
