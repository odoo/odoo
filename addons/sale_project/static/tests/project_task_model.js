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

export class SaleOrder extends models.Model {
    _name = "sale.order";

    name = fields.Char({ string: "name" });
    partner_id = fields.Many2one({ string: "Customer", relation: "res.partner" });
    project_id = fields.Many2one({ string: "Project", relation: "project.project" });
    order_line = fields.One2many({ relation: "sale.order.line" });

    _records = [{ id: 1, name: "Sales Order 1" }];
}

export class SaleOrderLine extends models.Model {
    _name = "sale.order.line";

    name = fields.Char({ related: "product_id.name" });
    product_id = fields.Many2one({ string: "Product", relation: "product.product" });

    _records = [{ id: 1, product_id: 1 }];
}

export class ProductProduct extends models.Model {
    _name = "product.product";

    name = fields.Char();
    type = fields.Selection({
        string: "Type",
        selection: [("consu", "Goods"), ("service", "Service"), ("combo", "Combo")],
    });

    _records = [
        { id: 1, name: "Service Product 1", type: "service" },
        { id: 2, name: "Consumable Product 1", type: "consu" },
        { id: 3, name: "Service Product 2", type: "service" },
    ];
}

Object.assign(projectModels, {
    ProjectMilestone,
    ProjectTask,
});
