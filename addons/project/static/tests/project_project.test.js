import { expect, test, describe } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    mountView,
    onRpc,
    contains,
    toggleKanbanColumnActions
} from "@web/../tests/web_test_helpers";

import { defineProjectModels, ProjectProject } from "./project_models";

defineProjectModels();
describe.current.tags("desktop");

const listViewParams = {
    resModel: "project.project",
    type: "list",
    actionMenus: {},
    arch: `
        <list multi_edit="1" js_class="project_project_list">
            <field name="name"/>
            <field name="is_user_project_manager"/>
        </list>
    `,
}

test("project.project (list) show archive/unarchive action for project manager", async () => {
    onRpc("has_group", ({ args }) => args[1] === "project.group_project_manager");
    await mountView(listViewParams);
    await contains("input.form-check-input").click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    expect("[data-icon='archive']").toHaveCount(1, { message: "Archive action should be visible" });
    expect("[data-icon='unarchive']").toHaveCount(1, { message: "Unarchive action should be visible" });
});

test("project.project (list) hide archive/unarchive action for project user", async () => {
    onRpc("has_group", ({ args }) => args[1] === "project.group_project_user");
    await mountView(listViewParams);
    await contains("input.form-check-input").click();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    expect(`.o-dropdown--menu span:contains(Archive)`).toHaveCount(0, { message: "Archive action should not be visible" });
    expect(`.o-dropdown--menu span:contains(Unarchive)`).toHaveCount(0, { message: "Unarchive action should not be visible" });
});

test("project.project (list) show archive/unarchive action for project user managing selection", async () => {
    onRpc("has_group", ({ args }) => args[1] === "project.group_project_user");
    ProjectProject._records.push({
        id: 99,
        name: "User-managed project",
        is_user_project_manager: true,
    });

    const expectArchiveActions = async (count, message) => {
        await contains(`.o_cp_action_menus .dropdown-toggle`).click();
        expect("[data-icon='archive']").toHaveCount(count, { message });
        expect("[data-icon='unarchive']").toHaveCount(count, { message });
        await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    };
    const toggleRow = (name) =>
        contains(`.o_data_row:contains('${name}') input.form-check-input`).click();

    await mountView(listViewParams);
    await toggleRow("Project 1");
    await expectArchiveActions(0, "Hidden when the selection holds a project the user does not manage");
    await toggleRow("User-managed project");
    await expectArchiveActions(0, "Hidden when the selection mixes managed and unmanaged projects");
    await toggleRow("Project 1");
    await expectArchiveActions(1, "Visible when the user manages every selected project");
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
    await expect('.o_column_archive_records').toHaveCount(0, { message: "Archive action should not be visible" });
    await expect('.o_column_unarchive_records').toHaveCount(0, { message: "Unarchive action should not be visible" });
});
