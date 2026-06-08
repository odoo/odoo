import { fields, models } from "@web/../tests/web_test_helpers";

export class ResRole extends models.ServerModel {
    _name = "res.role";

    name = fields.Char();
    user_ids = fields.Many2many({ relation: "res.users" });
    user_ids_count = fields.Integer({ compute: "_compute_user_ids_count" });

    _compute_user_ids_count() {
        for (const role of this) {
            role.user_ids_count = role.user_ids.length;
        }
    }
}
