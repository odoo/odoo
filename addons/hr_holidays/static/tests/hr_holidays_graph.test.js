import { describe, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";
import {
    checkDatasets,
    checkLabels,
    clickSort,
    selectMode,
} from "@web/../tests/views/graph/graph_test_helpers";
import { defineHrHolidaysModels } from "./hr_holidays_test_helpers";

describe.current.tags("desktop");

class HrLeaveReport extends models.Model {
    _name = "hr.leave.report";

    employee_id = fields.Many2one({ relation: "hr.employee" });
    leave_type = fields.Selection({
        selection: [
            ["allocation", "Allocation"],
            ["request", "Time Off"],
        ],
    });
    number_of_days = fields.Float();
    number_of_hours = fields.Float();

    // Jane first by days, Richard first by days + hours
    _records = [
        { employee_id: 100, leave_type: "allocation", number_of_days: 1, number_of_hours: 9 },
        { employee_id: 200, leave_type: "allocation", number_of_days: 2, number_of_hours: 3 },
    ];
}

defineHrHolidaysModels();
defineModels([HrLeaveReport]);

test("sorted bar graph only uses the displayed measure", async () => {
    // pie loads both measures, bar only displays the first one
    const view = await mountView({
        type: "graph",
        resModel: "hr.leave.report",
        arch: `<graph js_class="hr_holidays_graph" type="pie"><field name="employee_id"/><field name="leave_type"/></graph>`,
        context: { graph_measure: ["number_of_days", "number_of_hours"] },
    });
    await selectMode("bar");
    await clickSort("desc");
    checkLabels(view, ["Jane", "Richard"]);
    checkDatasets(view, "data", { data: [2, 1] });
});
