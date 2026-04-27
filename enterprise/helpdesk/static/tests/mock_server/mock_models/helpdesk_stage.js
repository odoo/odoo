import { fields, models } from "@web/../tests/web_test_helpers";

export class HelpdeskStage extends models.Model {
    _name = "helpdesk.stage";

    name = fields.Char({ string: "Name" });

    _records = [{ name: "Stage 1" }, { name: "Stage 2" }, { name: "Stage 3" }];
}
