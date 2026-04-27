import { clickCell } from "@web_gantt/../tests/web_gantt_test_helpers";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";
import { definePlanningModels, planningModels } from "@planning/../tests/planning_mock_models";
import { expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { queryFirst } from "@odoo/hoot-dom";

class SaleOrderLine extends models.Model {
    _name = "sale.order.line";

    state = fields.Char();

    _records = [{ state: "confirmed" }];
}
class PlanningSlot extends planningModels.PlanningSlot {
    sale_line_id = fields.Many2one({ string: "SOL", relation: "sale.order.line" });

    _records = [
        {
            name: "Slot 1",
            start_datetime: "2019-03-11 10:55:05",
            end_datetime: "2019-03-13 10:55:05",
            sale_line_id: 1,
        },
        {
            name: "Slot 2",
            sale_line_id: 1,
        },
    ];
}
planningModels.PlanningSlot = PlanningSlot;
definePlanningModels();
defineModels([SaleOrderLine]);

test("Slot should be instantly created on click when grouped by sale_line_id.", async () => {
    mockDate("2019-03-11 07:00:00", +1);
    onRpc("planning.slot", "gantt_resource_work_interval", () => {
        return [{ false: [] }, { false: false }, { false: 0 }];
    });
    await mountView({
        type: "gantt",
        resModel: "planning.slot",
        arch: `<gantt
                    js_class="planning_gantt"
                    date_start="start_datetime"
                    date_stop="end_datetime"
                    default_scale="week"
                />`,
        groupBy: ["sale_line_id"],
    });
    await clickCell("10 W11 2019", "sale.order.line,1");
    expect(queryFirst(".o_gantt_pill")).toHaveText("Slot 2");
});
