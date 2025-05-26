import { fields, models, getKwArgs } from "@web/../tests/web_test_helpers";

export class HrEmployee extends models.Model {
    _name = "hr.employee";

    name = fields.Char();
    department_id = fields.Many2one({ relation: "hr.department" });
    leave_date_to = fields.Date();
    user_id = fields.Many2one({ relation: "res.users" });

    _to_store(ids, store, fields) {
        const kwargs = getKwArgs(arguments, "id", "store", "fields");
        fields = kwargs.fields;
        for (const employee of this.browse(ids)) {
            const [data] = this._read_format(employee.id, fields);
            if (fields.includes("department_id")) {
                data.department_id = data.department_id[0];
            }
            store.add(this.browse(employee.id), data);
        }
    }

    _records = [
        {
            id: 100,
            name: "Richard",
            department_id: 11,
        },
        {
            id: 200,
            name: "Jane",
            department_id: 11,
        },
    ];
}
