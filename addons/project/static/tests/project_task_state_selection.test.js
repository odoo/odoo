import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountView } from "@web/../tests/web_test_helpers";

import { defineProjectModels } from "./project_models";

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
    expect("div[name='state']:first-child button.dropdown-toggle i.fa-times-circle").toBeDisplayed({
        message:
            "If the canceled state as been selected, the fa-times-circle icon should be displayed",
    });

    await click("div[name='state'] i.fa-hourglass-o");
    await animationFrame();
    expect(".o-dropdown--menu").toHaveCount(0, {
        message: "When trying to click on the waiting icon, no dropdown menu should display",
    });
});
