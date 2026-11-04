import { fields, models } from "@web/../tests/web_test_helpers";

export class ResourceTask extends models.Model {
    _name = "resource.task";

    display_name = fields.Char({ string: "Name" });
    resource_ids = fields.Many2many({ string: "Resources", relation: "resource.resource" });
    resource_id = fields.Many2one({ string: "Resource", relation: "resource.resource"});
    resource_type = fields.Char({ string: "Resource Type" });
}
