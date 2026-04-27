import { planningModels } from "@planning/../tests/planning_mock_models";
import { models, fields } from "@web/../tests/web_test_helpers";

export class PlanningSlot extends planningModels.PlanningSlot {
    _name = "planning.slot";

    sale_line_id = fields.Many2one({ relation: "sale.order.line" });
}

export class SaleOrderLine extends models.Model {
    _name = "sale.order.line";

    name = fields.Char();
}

planningModels.PlanningSlot = PlanningSlot;
planningModels.SaleOrderLine = SaleOrderLine;
