import { fields, models } from "@web/../tests/web_test_helpers";
import { projectModels } from "@project/../tests/project_models";


export class ProjectTask extends projectModels.ProjectTask {
    _name = "project.task";

    sale_line_id = fields.Many2one({ string: "Sale Order Line", relation: "sale.order.line" });
}

export class ProjectMilestone extends projectModels.ProjectMilestone {
    _name = "project.milestone";

    product_uom_qty = fields.Float({ string: "Quantity" });
    quantity_percentage = fields.Float({ string: "Percentage" });
}

export class SaleOrderLine extends models.Model {
    _name = "sale.order.line";

    name = fields.Char({ string: "name" });
}

Object.assign(projectModels, {
    ProjectMilestone,
    ProjectTask,
    SaleOrderLine,
});
