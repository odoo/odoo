import { expect, test } from "@odoo/hoot";

import { mountView } from "@web/../tests/web_test_helpers";

import { defineProjectModels } from "./project_models";

defineProjectModels();

test("ProjectMany2one: project.task form view with private task", async () => {
    await mountView({
        resModel: "project.task",
        resId: 3,
        type: "form",
        arch: `
            <form>
                <field name="name"/>
                <field name="project_id" widget="project"/>
            </form>
        `,
    });
    expect("div[name='project_id'] .o_many2one").toHaveClass("o_many2one private_placeholder w-100");
    expect("div[name='project_id'] .o_many2one input").toHaveAttribute("placeholder", "Private");
});

test("ProjectMany2one: project.task list view", async () => {
    await mountView({
        resModel: "project.task",
        type: "list",
        arch: `
            <list>
                <field name="name"/>
                <field name="project_id" widget="project"/>
            </list>
        `,
    });
    expect("div[name='project_id']").toHaveCount(3);
    expect("div[name='project_id'] .o_many2one").toHaveCount(2);
    expect("div[name='project_id'] span.text-danger.fst-italic.text-muted").toHaveCount(1);
    expect("div[name='project_id'] span.text-danger.fst-italic.text-muted").toHaveText("🔒 Private");
});
