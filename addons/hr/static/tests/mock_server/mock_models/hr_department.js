import { models, fields, getKwArgs } from "@web/../tests/web_test_helpers";

export class HrDepartment extends models.ServerModel {
    _name = "hr.department";
    _rec_name = "complete_name";

    name = fields.Char();
    complete_name = fields.Char({
        compute: "_compute_complete_name",
    });
    display_name = fields.Char({
        compute: "_compute_display_name",
    });

    _compute_complete_name() {
        for (const department of this) {
            department.complete_name = department.name;
        }
    }

    _compute_display_name() {
        this._compute_complete_name();
        for (const department of this) {
            department.display_name = department.complete_name;
        }
    }

    _to_store(ids, store, fields) {
        const kwargs = getKwArgs(arguments, "id", "store", "fields", "extra_fields");
        fields = kwargs.fields;
        if (!fields) {
            fields = ["name"];
        }
        for (const department of this.browse(ids)) {
            const [data] = this._read_format(department.id, fields);
            store.add(this.browse(department.id), data);
        }
    }
}
