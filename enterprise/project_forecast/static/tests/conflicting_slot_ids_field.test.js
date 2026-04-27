import { expect, test } from "@odoo/hoot";
import { queryText } from "@odoo/hoot-dom";

import { mountView } from "@web/../tests/web_test_helpers";
import { definePlanningModels, planningModels } from "@planning/../tests/planning_mock_models";

import {
    PlanningSlot as ProjectForecastPlanningSlot,
    ProjectProject as ProjectForecastProjectProject,
} from "./project_forecast_mock_models";

class PlanningSlot extends ProjectForecastPlanningSlot {
    _records = [
        {
            id: 1,
            conflicting_slot_ids: [2],
        },
        {
            id: 2,
            start_datetime: "2021-09-01 08:00:00",
            end_datetime: "2021-09-01 12:00:00",
            allocated_hours: 4,
            allocated_percentage: 100,
            project_id: 1,
        },
    ];

    _views = {
        form: `<form><field name="conflicting_slot_ids" widget="conflicting_slot_ids"/></form>`,
    };
}

class ProjectProject extends ProjectForecastProjectProject {
    _records = [{ id: 1, name: "Project 1" }];
}

planningModels.PlanningSlot = PlanningSlot;
planningModels.ProjectProject = ProjectProject;

definePlanningModels();

test("Test the conflict slot message content", async () => {
    await mountView({
        resId: 1,
        resModel: "planning.slot",
        type: "form",
    });

    expect(".o_conflicting_slot").toHaveCount(1);
    expect(queryText(".o_conflicting_slot")).toBe(
        "09/01/2021 09:00:0009/01/2021 13:00:00\n(4h) (100.00%) - Project 1"
    );
});
