import { fields, models, getKwArgs } from "@web/../tests/web_test_helpers";

export class HrEmployee extends models.ServerModel {
    _name = "hr.employee";

    department_id = fields.Many2one({ relation: "hr.department" });
    work_email = fields.Char();
    work_phone = fields.Char();
    work_location_type = fields.Char();
    work_location_id = fields.Many2one({ relation: "hr.work.location" });
    job_title = fields.Char();

    _to_store(ids, store, fields) {
        const kwargs = getKwArgs(arguments, "id", "store", "fields");
        fields = kwargs.fields;
        for (const employee of this.browse(ids)) {
            const [data] = this._read_format(employee.id, fields);
            if (fields.includes("department_id")) {
                data.department_id = data.department_id[0];
            }
            if (fields.includes("work_location_id")) {
                data.work_location_id = data.work_location_id[0];
            }
            store.add(this.browse(employee.id), data);
        }
    }

    _views = {
        search: `<search><field name="display_name" string="Name" /></search>`,
        list: `<list><field name="display_name"/></list>`,
    };
}
