import { fields, models } from "@web/../tests/web_test_helpers";

export class MailCallArtifact extends models.Model {
    _name = "mail.call.artifact";

    media_id = fields.Many2one({ relation: "ir.attachment" });
    start_ms = fields.Integer();
    end_ms = fields.Integer();
    discuss_call_history_id = fields.Many2one({ relation: "discuss.call.history" });
}
