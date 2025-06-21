import { expect, test, describe } from "@odoo/hoot";
import { click, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import { mountView } from "@web/../tests/web_test_helpers";

import { defineProjectModels, ProjectTask } from "./project_models";

describe.current.tags("desktop");
defineProjectModels();

test("project.task (kanban): check task state widget", async () => {
    await mountView({
        resModel: "project.task",
        type: "kanban",
        arch: `
            <kanban js_class="project_task_kanban">
                <templates>
                    <t t-name="card">
                        <field name="state" widget="project_task_state_selection" class="project_task_state_test"/>
                    </t>
                </templates>
            </kanban>
        `,
    });

    expect(".o-dropdown--menu").toHaveCount(0, {
        message: "If the state button has not been pressed yet, no dropdown should be displayed",
    });
    await click("div[name='state']:first-child button.dropdown-toggle");
    await animationFrame();
    expect(".o-dropdown--menu").toHaveCount(1, {
        message: "Once the button has been pressed the dropdown should appear",
    });

    await click(".o-dropdown--menu span.text-danger");
    await animationFrame();
    expect("div[name='state']:first-child button.dropdown-toggle i.fa-times-circle").toBeVisible({
        message:
            "If the canceled state as been selected, the fa-times-circle icon should be displayed",
    });

    await click("div[name='state'] i.fa-hourglass-o");
    await animationFrame();
    expect(".o-dropdown--menu").toHaveCount(0, {
        message: "When trying to click on the waiting icon, no dropdown menu should display",
    });
});

test("project.task (form): check task state widget", async () => {
    ProjectTask._views = {
        form: `<form js_class="project_task_form">
                    <field name="project_id"/>
                    <field name="name"/>
                    <field name="state" widget="project_task_state_selection" nolabel="1"/>
                </form>`,
    };
    await mountView({
        resModel: "project.task",
        resId: 1,
        type: "form",
    });
    await click("button.o_state_button");
    await animationFrame();
    expect(queryAllTexts(".state_selection_field_menu > .dropdown-item")).toEqual([
        "In Progress",
        "Changes Requested",
        "Approved",
        "Cancelled",
        "Done",
    ]);
    await click("button.o_state_button");

    await mountView({
        resModel: "project.task",
        resId: 3,
        type: "form",
    });
    await click("button.o_state_button:contains('Waiting')");
    await animationFrame();
    expect(queryAllTexts(".state_selection_field_menu > .dropdown-item")).toEqual([
        "Cancelled",
        "Done",
    ]);
});
