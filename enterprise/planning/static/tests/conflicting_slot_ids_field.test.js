import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";

import { mountView } from "@web/../tests/web_test_helpers";
import { definePlanningModels, planningModels } from "./planning_mock_models";

class PlanningSlot extends planningModels.PlanningSlot {
    _records = [
        {
            id: 1,
            start_datetime: "2021-09-01 08:00:00",
            end_datetime: "2021-09-01 12:00:00",
            allocated_hours: 4,
            allocated_percentage: 100,
            role_id: 1,
            conflicting_slot_ids: [2, 3],
        },
        {
            id: 2,
            start_datetime: "2021-09-01 08:00:00",
            end_datetime: "2021-09-01 12:00:00",
            allocated_hours: 4,
            allocated_percentage: 100,
            role_id: 1,
            conflicting_slot_ids: [1, 3],
        },
        {
            id: 3,
            start_datetime: "2021-09-01 10:00:00",
            end_datetime: "2021-09-01 13:00:00",
            allocated_hours: 2,
            allocated_percentage: 66.67,
            role_id: false,
            conflicting_slot_ids: [1, 2, 4, 5, 6, 7],
        },
        {
            id: 4,
            start_datetime: "2021-09-01 12:30:00",
            end_datetime: "2021-09-01 17:30:00",
            allocated_hours: 5,
            allocated_percentage: 100,
            role_id: 1,
            conflicting_slot_ids: [3, 5, 6],
        },
        {
            id: 5,
            start_datetime: "2021-09-01 12:30:00",
            end_datetime: "2021-09-01 17:30:00",
            allocated_hours: 5,
            allocated_percentage: 100,
            role_id: false,
            conflicting_slot_ids: [3, 4, 6],
        },
        {
            id: 6,
            start_datetime: "2021-09-01 12:30:00",
            end_datetime: "2021-09-01 18:00:00",
            allocated_hours: 5.5,
            allocated_percentage: 100,
            role_id: false,
            conflicting_slot_ids: [3, 4, 5],
        },
        {
            id: 7,
            start_datetime: "2021-09-01 12:30:00",
            end_datetime: "2021-09-01 17:30:00",
            allocated_hours: 5,
            allocated_percentage: 100,
            role_id: false,
            conflicting_slot_ids: [3, 4, 5],
        },
    ];

    _views = {
        form: `<form><field name="conflicting_slot_ids" widget="conflicting_slot_ids"/></form>`,
    };
}

class PlanningRole extends planningModels.PlanningRole {
    _records = [{ id: 1, name: "Developer" }];
}

planningModels.PlanningSlot = PlanningSlot;
planningModels.PlanningRole = PlanningRole;

definePlanningModels();

test("display conflicting slot ids field in the form view", async () => {
    await mountView({
        resId: 1,
        resModel: "planning.slot",
        type: "form",
    });

    expect(".o_field_conflicting_slot_ids[name=conflicting_slot_ids]").toHaveCount(1);
    expect(".o_field_conflicting_slot_ids > p").toHaveText(
        "Prepare for the ultimate multi-tasking challenge:"
    );
    expect(".o_conflicting_slot").toHaveCount(2);
    expect(queryAllTexts(".o_conflicting_slot")).toEqual([
        "09/01/2021 09:00:0009/01/2021 13:00:00\n(4h) (100.00%) - Developer",
        "09/01/2021 11:00:0009/01/2021 14:00:00\n(2h) (66.67%)",
    ]);
});

test("display 5 shifts in conflict", async () => {
    await mountView({
        resId: 3,
        resModel: "planning.slot",
        type: "form",
    });

    expect(".o_field_conflicting_slot_ids[name=conflicting_slot_ids]").toHaveCount(1);
    expect(".o_field_conflicting_slot_ids > p").toHaveText(
        "Prepare for the ultimate multi-tasking challenge:"
    );
    expect(".o_conflicting_slot").toHaveCount(5);
    expect(queryAllTexts(".o_conflicting_slot")).toEqual([
        "09/01/2021 09:00:0009/01/2021 13:00:00\n(4h) (100.00%) - Developer",
        "09/01/2021 09:00:0009/01/2021 13:00:00\n(4h) (100.00%) - Developer",
        "09/01/2021 13:30:0009/01/2021 18:30:00\n(5h) (100.00%) - Developer",
        "09/01/2021 13:30:0009/01/2021 18:30:00\n(5h) (100.00%)",
        "09/01/2021 13:30:0009/01/2021 19:00:00\n(5h30) (100.00%)",
    ]);
});
