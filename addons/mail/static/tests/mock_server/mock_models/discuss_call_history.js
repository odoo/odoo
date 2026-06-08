import { fields, models } from "@web/../tests/web_test_helpers";

export class DiscussCallHistory extends models.Model {
    _name = "discuss.call.history";

    start_date = fields.Datetime();
    end_date = fields.Datetime();
    artifact_ids = fields.One2many({
        relation: "mail.call.artifact",
        relation_field: "discuss_call_history_id",
    });
}
