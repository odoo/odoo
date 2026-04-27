import { expect, test, beforeEach, describe } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";

import { mountView } from "@web/../tests/web_test_helpers";

import { defineProjectModels, projectModels } from "@project/../tests/project_models";

describe.current.tags("desktop");
defineProjectModels();

const { ProjectTask } = projectModels;

beforeEach(() => {
    mockDate("2024-01-03 08:00:00", +0);
});

test("Check that FsmDateWidget is displaying information in the correct format", async () => {
    ProjectTask._records = [
        {
            id: 1,
            planned_date_begin: "2024-01-10 06:30:00",
            date_deadline: "2024-01-10 11:30:00",
            stage_id: 2,
        },
        {
            id: 2,
            planned_date_begin: "2024-01-01 06:00:00",
            date_deadline: "2024-01-01 12:30:00",
            stage_id: 2,
        },
    ];

    await mountView({
        resModel: "project.task",
        type: "kanban",
        arch: `
            <kanban>
                <field name="date_deadline"/>
                <field name="stage_id"/>
                <template>
                    <t t-name="card">
                        <field name="planned_date_begin" widget="fsm_date"/>
                    </t>
                </template>
            </kanban>
        `,
    });
    expect(
        '.o_kanban_record:first-child div[name="planned_date_begin"]:contains("06:30")'
    ).toHaveCount(1, {
        message: "The format of the planned_date_begin of the record should be HH:MM",
    });
    expect(
        '.o_kanban_record:first-child div[name="planned_date_begin"] .oe_kanban_text_red'
    ).toHaveCount(0, {
        message:
            "If the deadline of the record has not passed already the hour shouldn't be displayed in red",
    });
    expect(
        '.o_kanban_record:nth-child(2) div[name="planned_date_begin"] .oe_kanban_text_red'
    ).toHaveCount(1, {
        message:
            "If the deadline of the record has already passed the hour should be displayed in red",
    });
});
