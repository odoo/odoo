import { expect, test, beforeEach, describe } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";

import { defineModels, mountView, onRpc } from "@web/../tests/web_test_helpers";

import { mailModels } from "@mail/../tests/mail_test_helpers";

import { planningModels, definePlanningModels } from "@planning/../tests/planning_mock_models";

import { Contract } from "@planning_contract/../tests/planning_contract_gantt/planning_contract_gantt_mock_model";

defineModels([Contract]);
definePlanningModels();

const { PlanningSlot, ResourceResource, HrEmployee } = planningModels;
const { ResUsers } = mailModels;

describe.current.tags("desktop");

beforeEach(() => {
    mockDate("2024-03-27");

    PlanningSlot._records.push({
        id: 1,
        name: "Shift-1",
        state: "published",
        resource_id: 1,
        start_datetime: "2024-03-27 02:30:00",
        end_datetime: "2024-03-27 11:30:00",
    });

    ResourceResource._records.push({
        id: 1,
        name: "Pig-1",
        user_id: 99,
        resource_type: "user",
        employee_id: 1,
    });

    HrEmployee._records.push({
        id: 1,
        user_id: 99,
        name: "Pig-1",
        resource_id: 1,
    });
    ResUsers._records.push({
        id: 99,
    });
});

const ganttViewParams = {
    resModel: "planning.slot",
    type: "gantt",
    arch: `<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" default_group_by="resource_id"
                default_scale="week" display_unavailability="1" total_row="True">
           </gantt>`,
    context: {
        default_start_date: "2024-03-24",
        default_stop_date: "2024-03-30",
    },
};

onRpc(async ({ args, method, model, parent }) => {
    if (method === "gantt_resource_work_interval") {
        return [
            {
                1: [
                    ["2024-03-25 09:00:00", "2024-03-25 18:00:00"],
                    ["2024-03-25 09:00:00", "2024-03-25 18:00:00"],
                    ["2024-03-26 09:00:00", "2024-03-26 18:00:00"],
                    ["2024-03-26 09:00:00", "2024-03-26 18:00:00"],
                    ["2024-03-27 09:00:00", "2024-03-27 18:00:00"],
                    ["2024-03-27 09:00:00", "2024-03-27 18:00:00"],
                    ["2024-03-28 09:00:00", "2024-03-28 18:00:00"],
                    ["2024-03-28 09:00:00", "2024-03-28 18:00:00"],
                    ["2024-03-29 09:00:00", "2024-03-29 18:00:00"],
                    ["2024-03-29 09:00:00", "2024-03-29 18:00:00"],
                ],
                false: [
                    ["2024-03-25 09:00:00", "2024-03-25 18:00:00"],
                    ["2024-03-25 09:00:00", "2024-03-25 18:00:00"],
                    ["2024-03-26 09:00:00", "2024-03-26 18:00:00"],
                    ["2024-03-26 09:00:00", "2024-03-26 18:00:00"],
                    ["2024-03-27 09:00:00", "2024-03-27 18:00:00"],
                    ["2024-03-27 09:00:00", "2024-03-27 18:00:00"],
                    ["2024-03-28 09:00:00", "2024-03-28 18:00:00"],
                    ["2024-03-28 09:00:00", "2024-03-28 18:00:00"],
                    ["2024-03-29 09:00:00", "2024-03-29 18:00:00"],
                    ["2024-03-29 09:00:00", "2024-03-29 18:00:00"],
                ],
            },
            { false: 0, 1: 0 },
            { false: 0, 1: 9 },
        ];
    } else if (method === "get_gantt_data") {
        const result = await parent();
        result.unavailabilities = {
            resource_id: {
                1: [
                    { start: "2024-03-23 18:00:00", stop: "2024-03-25 09:00:00" },
                    { start: "2024-03-28 18:00:00", stop: "2024-04-01 09:00:00" },
                ],
                false: [
                    { start: "2024-03-23 18:00:00", stop: "2024-03-25 09:00:00" },
                    { start: "2024-03-28 18:00:00", stop: "2024-04-01 09:00:00" },
                ],
            },
        };
        return result;
    }
});
/*
    The following cases are to be checked/tested.
╔══════════╦══════════╦══════════════════╦══════════════════════════════════════════════════════╗
║ Employee ║ Contract ║ Status           ║ Behaviour                                            ║
╠══════════╬══════════╬══════════════════╬══════════════════════════════════════════════════════╣
║ 1        ║ No       ║ None             ║ White it in working days and grey according          ║
║          ║          ║                  ║ to the employee calendar                             ║
╠══════════╬══════════╬══════════════════╬══════════════════════════════════════════════════════╣
║ 2        ║ Yes      ║ Draft + state in ║ White it in working days and grey according          ║
║          ║          ║ normal           ║ to the employee calendar                             ║
╠══════════╬══════════╬══════════════════╬══════════════════════════════════════════════════════╣
║ 3        ║ Yes      ║ Draft + state in ║ White it in working days and grey according          ║
║          ║          ║ blocked          ║ to the employee calendar                             ║
╠══════════╬══════════╬══════════════════╬══════════════════════════════════════════════════════╣
║ 4        ║ Yes      ║ Draft + state    ║ White & grey during the contract period according to ║
║          ║          ║ in ready         ║ the employee calendar, and grey everywhere outside   ║
║          ║          ║                  ║ of the contract period                               ║
╠══════════╬══════════╬══════════════════╬══════════════════════════════════════════════════════╣
║ 5        ║ Yes      ║ Running          ║ White & grey during the contract period according to ║
║          ║          ║                  ║ the employee calendar, and grey everywhere outside   ║
║          ║          ║                  ║ of the contract period                               ║
╠══════════╬══════════╬══════════════════╬══════════════════════════════════════════════════════╣
║ 6        ║ Yes      ║ Expired          ║ White & grey during the contract period according to ║
║          ║          ║                  ║ the employee calendar, and grey everywhere outside   ║
║          ║          ║                  ║ of the contract period                               ║
╠══════════╬══════════╬══════════════════╬══════════════════════════════════════════════════════╣
║ 7        ║ Yes      ║ Cancelled        ║ White & grey during the contract period according to ║
║          ║          ║                  ║ the employee calendar, and grey everywhere outside   ║
║          ║          ║                  ║ of the contract period                               ║
╚══════════╩══════════╩══════════════════╩══════════════════════════════════════════════════════╝
*/
test("check gantt shading for employee without contract (case-1)", async () => {
    await mountView(ganttViewParams);
    expect(".o_gantt_cell[data-row-id*='Pig-1'][style*='Gantt__DayOff']").toHaveCount(3);
    expect(".o_gantt_cell[data-row-id*='Pig-1']:not([style*='Gantt__DayOff'])").toHaveCount(4);
});

test("check gantt shading for employee without contract (case-2)", async () => {
    Object.assign(Contract._records[0], {
        state: "draft",
        date_start: "2024-03-28 00:00:00",
        date_end: "2024-03-28 23:50:59",
        kanban_state: "normal",
    });
    await mountView(ganttViewParams);
    expect(".o_gantt_cell[data-row-id*='Pig-1'][style*='Gantt__DayOff']").toHaveCount(3);
    expect(".o_gantt_cell[data-row-id*='Pig-1']:not([style*='Gantt__DayOff'])").toHaveCount(4);
});

test("check gantt shading for employee without contract (case-3)", async () => {
    Object.assign(Contract._records[0], {
        state: "draft",
        date_start: "2024-03-28 00:00:00",
        date_end: "2024-03-28 23:50:59",
        kanban_state: "blocked",
    });
    await mountView(ganttViewParams);
    expect(".o_gantt_cell[data-row-id*='Pig-1'][style*='Gantt__DayOff']").toHaveCount(3);
    expect(".o_gantt_cell[data-row-id*='Pig-1']:not([style*='Gantt__DayOff'])").toHaveCount(4);
});

test("check gantt shading for employee without contract (case-4)", async () => {
    Object.assign(Contract._records[0], {
        state: "draft",
        date_start: "2024-03-28 00:00:00",
        date_end: "2024-03-28 23:50:59",
        kanban_state: "done",
    });
    await mountView(ganttViewParams);
    expect(".o_gantt_cell[data-row-id*='Pig-1'][style*='Gantt__DayOff']").toHaveCount(3);
    expect(".o_gantt_cell[data-row-id*='Pig-1']:not([style*='Gantt__DayOff'])").toHaveCount(4);
});

test("check gantt shading for employee without contract (case-5)", async () => {
    Object.assign(Contract._records[0], {
        state: "open",
        date_start: "2024-03-27 00:00:00",
        date_end: "2024-03-29 23:59:59",
        kanban_state: "done",
    });
    await mountView(ganttViewParams);
    expect(".o_resource_has_no_working_periods").toHaveCount(3);
    expect(
        ".o_gantt_cell[data-row-id*='Pig-1'][style*='Gantt__DayOff']:not(.o_resource_has_no_working_periods)"
    ).toHaveCount(2);
    expect(
        ".o_gantt_cell[data-row-id*='Pig-1']:not([style*='Gantt__DayOff']):not(.o_resource_has_no_working_periods)"
    ).toHaveCount(2);
});

test("check gantt shading for employee without contract (case-6)", async () => {
    Object.assign(Contract._records[0], {
        state: "close",
        date_start: "2024-03-27 00:00:00",
        date_end: "2024-03-29 23:59:59",
        kanban_state: "done",
    });
    await mountView(ganttViewParams);
    expect(".o_resource_has_no_working_periods").toHaveCount(3);
    expect(
        ".o_gantt_cell[data-row-id*='Pig-1'][style*='Gantt__DayOff']:not(.o_resource_has_no_working_periods)"
    ).toHaveCount(2);
    expect(
        ".o_gantt_cell[data-row-id*='Pig-1']:not([style*='Gantt__DayOff']):not(.o_resource_has_no_working_periods)"
    ).toHaveCount(2);
});

test("check gantt shading for employee without contract (case-7)", async () => {
    Object.assign(Contract._records[0], {
        state: "cancel",
        date_start: "2024-03-27 00:00:00",
        date_end: "2024-03-29 23:59:59",
        kanban_state: "normal",
    });
    await mountView(ganttViewParams);
    expect(".o_resource_has_no_working_periods").toHaveCount(0);
    expect(
        ".o_gantt_cell[data-row-id*='Pig-1'][style*='Gantt__DayOff']:not(.o_resource_has_no_working_periods)"
    ).toHaveCount(3);
    expect(
        ".o_gantt_cell[data-row-id*='Pig-1']:not([style*='Gantt__DayOff']):not(.o_resource_has_no_working_periods)"
    ).toHaveCount(4);
});
