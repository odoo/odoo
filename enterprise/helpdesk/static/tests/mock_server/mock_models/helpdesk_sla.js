import { fields, models } from "@web/../tests/web_test_helpers";

export class HelpdeskSla extends models.Model {
    _name = "helpdesk.sla";

    name = fields.Char();

    _records = [{ name: "SLA 1" }, { name: "SLA 2" }];
}
