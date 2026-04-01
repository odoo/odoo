import { fields, models } from "@web/../tests/web_test_helpers";

export class M2xAvatarUser extends models.Model {
    _name = "m2x.avatar.user";

    user_id = fields.Many2one({ relation: "res.users" });
    partner_id = fields.Many2one({ relation: "res.partner" });
    user_ids = fields.Many2many({ relation: "res.users", string: "Users" });
}
