import { beforeEach, expect, test } from "@odoo/hoot";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { openReport } from "@point_of_sale/../tests/unit/backend/reports/utils";

definePosModels();

beforeEach(() => {
    // Extend the shared report metadata with the filter added by pos_hr.
    onRpc("pos.report", "get_report_info", async ({ parent }) => {
        const info = await parent();
        info.filters.push({
            type: "single_select",
            key: "employee_id",
            model: "hr.employee",
            label: "Employee",
        });
        return info;
    });
});

test("filters and unfolds by employee", async () => {
    const report = await openReport();

    await contains("button:contains('Employee')").click();
    await contains(".pos_report_filter.singleselect input").click();
    await contains(".o-autocomplete--dropdown-item:contains('Employee1')").click();
    expect(report.options().employee_id).toBe(3);

    await contains(".line_level_1 .o_report_name_cell").click();
    expect(".line_level_2").toHaveCount(2);
});

test("keeps other report options unchanged", async () => {
    onRpc("pos.report", "get_report_info", async ({ parent }) => ({
        ...(await parent()),
        handler: "pos.report.handler",
    }));
    await openReport();
    await contains("button:contains('Options')").click();
    expect(".dropdown-item:contains('Unfold All')").toHaveCount(1);
    expect(".dropdown-item:contains('Export Employee-wise')").toHaveCount(0);
});
