import { test } from "@odoo/hoot";
import { session } from "@web/session";
import { mountView, patchWithCleanup } from "@web/../tests/web_test_helpers";

import { defineTimesheetModels } from "./hr_timesheet_models";
import { checkDatasets } from "@web/../tests/views/graph/graph_test_helpers";

defineTimesheetModels();

test("hr.timesheet (graph): data are not multiplied by a company related factor (factor === 1)", async () => {
    patchWithCleanup(session.user_companies.allowed_companies[1], {
        timesheet_uom_factor: 1,
    });

    const graph = await mountView({
        resModel: "account.analytic.line",
        type: "graph",
    });

    checkDatasets(graph, "data", { data: [8] });
});

test("hr.timesheet (graph): data are multiplied by a company related factor (factor !== 1)", async () => {
    patchWithCleanup(session.user_companies.allowed_companies[1], {
        timesheet_uom_factor: 0.125,
    });

    const graph = await mountView({
        resModel: "account.analytic.line",
        type: "graph",
    });

    checkDatasets(graph, "data", { data: [1] });
});
