import { fields, models } from "@web/../tests/web_test_helpers";

export class DiscussCallHistory extends models.Model {
    _name = "discuss.call.history";

    artifact_ids = fields.One2many({
        relation: "mail.call.artifact",
        relation_field: "discuss_call_history_id",
    });
    duration_hour = fields.Float();
    end_date = fields.Datetime();
    has_audio = fields.Boolean();
    has_recording = fields.Boolean();
    has_video = fields.Boolean();
    start_date = fields.Datetime();
}
