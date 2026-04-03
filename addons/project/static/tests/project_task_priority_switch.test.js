import { expect, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountView } from "@web/../tests/web_test_helpers";

import { ProjectTask, defineProjectModels } from "./project_models";

defineProjectModels();

test("project.task (form): check ProjectTaskPrioritySwitch", async () => {
    ProjectTask._records = [{ id: 1, priority: "0" }];

    await mountView({
        resModel: "project.task",
        type: "form",
        arch: `
            <form class="o_kanban_test">
                <field name="priority" widget="priority_switch"/>
            </form>
        `,
    });

    expect("div[name='priority'] [data-icon='star']").toHaveCount(1, {
        message: "The low priority should display the star (empty) icon",
    });
    await press("alt+r");
    await animationFrame();
    expect("div[name='priority'] [data-icon='star'].oi-filled").toHaveCount(1, {
        message:
            "After using the alt+r hotkey the priority should be set to high and the widget should display the star (filled) icon",
    });
});
