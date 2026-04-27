import { fields, models } from "@web/../tests/web_test_helpers";

export class WhatsAppTemplate extends models.ServerModel {
    _name = "whatsapp.template";

    model_id = fields.Many2one({
        relation: "ir.model",
        default: () => this.env["ir.model"].search([["model", "=", "res.partner"]])[0],
    });
}
