import { expect, test, beforeEach } from "@odoo/hoot";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import { click } from "@odoo/hoot-dom";

import { onRpc, mountView, mockService } from "@web/../tests/web_test_helpers";

import { defineProjectModels, projectModels } from "@project/../tests/project_models";

defineProjectModels();

function mockActionService(doActionStep) {
    const fakeActionService = {
        doAction: async (actionRequest, options = {}) => {
            expect(actionRequest).toBe("industry_fsm.project_task_fsm_mobile_server_action");
            expect.step(doActionStep);
        },
    };
    mockService("action", fakeActionService);
}

const { ProjectTask } = projectModels;

beforeEach(() => {
    onRpc("get_all_deadlines", () => ({ milestone_id: [], project_id: [] }));
    mockDate("2024-01-03 07:00:00");
    ProjectTask._records = [
        {
            id: 1,
            name: "Custom Mobile Button Test",
            planned_date_begin: "2024-01-01 06:00:00",
            date_deadline: "2024-01-02 12:30:00",
        },
    ];

    ProjectTask._views = {
        form: `
            <form>
                <field name="name"/>
                <field name="planned_date_begin"/>
                <field name="date_deadline"/>
            </form>
        `,
    };
});

test.tags("desktop");
test("fsm task gantt view", async () => {
    const now = luxon.DateTime.now();

    await mountView({
        resModel: "project.task",
        arch: '<gantt date_start="planned_date_begin" date_stop="date_deadline" js_class="task_gantt" />',
        type: "gantt",
        context: { fsm_mode: true },
    });

    expect(".o_gantt_view").toHaveCount(1);
    expect(".modal").toHaveCount(0);
    await click(".o_gantt_button_add.btn-primary");
    await animationFrame();
    expect(".modal").toHaveCount(1);
    expect(".modal .o_field_widget[name=planned_date_begin] .o_input").toHaveValue(
        now.toFormat("MM/dd/yyyy 00:00:00"),
        {
            message:
                "The fsm_mode present in the view context should set the start_datetime to the current day instead of the first day of the gantt view",
        }
    );
});

test.tags("mobile");
test("test custom action for edit gantt popover button", async () => {
    const doActionStep = "doAction";
    mockActionService(doActionStep);

    await mountView({
        arch: '<gantt date_start="planned_date_begin" date_stop="date_deadline" js_class="fsm_task_gantt" />',
        resModel: "project.task",
        type: "gantt",
        context: { fsm_mode: true },
    });

    expect(".o_gantt_pill").toHaveCount(1);
    click(".o_gantt_pill");
    await animationFrame();
    expect(".o_popover .popover-header").toHaveText("Custom Mobile Button Test");
    click(".o_popover .popover-footer button", { text: "Edit" });
    await animationFrame();

    expect.verifySteps([doActionStep]);
});
