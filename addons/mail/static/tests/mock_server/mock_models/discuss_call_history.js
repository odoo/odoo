import { fields, models } from "@web/../tests/web_test_helpers";

export class DiscussCallHistory extends models.ServerModel {
    _name = "discuss.call.history";

    artifact_ids = fields.One2many({
        relation: "mail.call.artifact",
        relation_field: "discuss_call_history_id",
    });
    end_date = fields.Datetime();
    start_date = fields.Datetime();
}
