import { fields, models } from "@web/../tests/web_test_helpers";

export class Partner extends models.Model {
    _name = "partner";

    message = fields.Char();
    foo = fields.Char();
    mobile = fields.Char();
    partner_ids = fields.One2many({ relation: "partner" });
}
