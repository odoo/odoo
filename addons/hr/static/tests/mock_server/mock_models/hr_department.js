import { models, fields } from "@web/../tests/web_test_helpers";

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

    get _to_store_defaults() {
        return ["name"];
    }
}
