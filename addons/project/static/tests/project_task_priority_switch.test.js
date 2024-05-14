import { describe, expect, test } from "@odoo/hoot";
import { mountView } from "@web/../tests/web_test_helpers";
import { defineProjectModels } from "@project/../tests/project_test_helpers";
import { press } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

describe.current.tags("desktop");
defineProjectModels();

test("Check whether task priority shortcut works as intended", async () => {
    await mountView({
        resModel: "project.task",
        type: "form",
        arch: `
            <form class="o_kanban_test">
               <field name="priority" widget="priority_switch"/>
            </form>`,
    });
    expect("div[name='priority'] a").toHaveClass("fa-star-o");
    press(["alt", "r"]);
    await animationFrame();
    expect("div[name='priority'] a").toHaveClass("fa-star");
});
