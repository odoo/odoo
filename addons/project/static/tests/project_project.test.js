import { expect, test, describe } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    mountView,
    onRpc,
    contains,
    toggleActionMenu,
    toggleKanbanColumnActions
} from "@web/../tests/web_test_helpers";

import { defineProjectModels } from "./project_models";

defineProjectModels();
describe.current.tags("desktop");

test("project.project (form) hide archive action for project user", async () => {
    onRpc("has_group", ({ args }) => args[1] === "project.group_project_user");

    await mountView({
        resModel: "project.project",
        type: "form",
        actionMenus: {},
        arch: `
            <form js_class="project_project_form">
                <field name="active"/>
                <field name="name"/>
            </form>
        `,
    });

    await toggleActionMenu();
    expect(`.o-dropdown--menu span:contains(Archive)`).toHaveCount(0);
});

const listViewParams = {
    resModel: "project.project",
    type: "list",
    actionMenus: {},
    arch: `
        <list multi_edit="1" js_class="project_project_list">
            <field name="name"/>
        </list>
    `,
}

test("project.project (list) show archive/unarchive action for project manager", async () => {
    onRpc("has_group", ({ args }) => args[1] === "project.group_project_manager");
    await mountView(listViewParams);
    await contains("input.form-check-input").click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    expect(`.oi-archive`).toHaveCount(1);
    expect(`.oi-unarchive`).toHaveCount(1);
});

test("project.project (list) hide archive/unarchive action for project user", async () => {
    onRpc("has_group", ({ args }) => args[1] === "project.group_project_user");

    await mountView(listViewParams);

    await contains("input.form-check-input").click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    expect(`.o-dropdown--menu span:contains(Archive)`).toHaveCount(0);
    expect(`.o-dropdown--menu span:contains(Unarchive)`).toHaveCount(0);
});

test("project.project (kanban) hide archive/unarchive action for project user", async () => {
    onRpc("has_group", ({ args }) => args[1] === "project.group_project_user");

    await mountView({
        resModel: "project.project",
        type: "kanban",
        actionMenus: {},
        arch: `
            <kanban js_class="project_project_kanban">
                <field name="stage_id"/>
                <templates>
                    <t t-name="card">
                        <div>
                            <field name="name"/>
                        </div>
                    </t>
                </templates>
            </kanban>
        `,
        groupBy: ['stage_id']
    });

    toggleKanbanColumnActions();
    await animationFrame();
    await expect('.o_column_archive_records').toHaveCount(0);
    await expect('.o_column_unarchive_records').toHaveCount(0);
});
