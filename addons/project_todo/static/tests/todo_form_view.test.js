import { expect, test, beforeEach } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";

import { mountView, contains, onRpc } from "@web/../tests/web_test_helpers";

import { defineTodoModels } from "./todo_test_helpers";
import { ProjectTask } from "./mock_server/mock_models/project_task";

defineTodoModels();

beforeEach(() => {
    ProjectTask._views = {
        list: `
            <list js_class="todo_list">
                <field name="name" nolabel="1"/>
                <field name="state" widget="todo_done_checkmark" nolabel="1"/>
            </list>`,
        form: `
            <form string="To-do" class="o_todo_form_view" js_class="todo_form">
                <field name="name"/>
                <field name="priority" invisible="1"/>
            </form>`,
        search: `
            <search/>`,
    };
});

test("Check that project_task_action_convert_todo_to_task appears in the menu actions if the user does belong to the group_project_user group", async () => {
    onRpc("has_group", () => true);
    await mountView({
        resModel: "project.task",
        resId: 1,
        type: "form",
        actionMenus: {},
    });

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    const menuActions = Array.from(queryAllTexts(".o-dropdown--menu span"));
    expect(menuActions.includes("Convert to Task")).toBe(true, {
        message:
            "project_task_action_convert_todo_to_task action should appear in the menu actions",
    });
});

test("Check that project_task_action_convert_todo_to_task does not appear in the menu actions if the user does not belong to the group_project_user group", async () => {
    onRpc("has_group", () => false);

    await mountView({
        resModel: "project.task",
        resId: 1,
        type: "form",
        actionMenus: {},
    });

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    const menuActions = Array.from(queryAllTexts(".o-dropdown--menu span"));
    expect(menuActions.includes("Convert to Task")).toBe(false, {
        message:
            "project_task_action_convert_todo_to_task action should appear in the menu actions",
    });
});
