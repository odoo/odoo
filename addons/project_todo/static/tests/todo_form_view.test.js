import { expect, test, beforeEach } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import { mountView, onRpc, mountWithCleanup, getService, contains } from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

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
                <field name="date_deadline" widget="remaining_days"/>
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

test("Check that todo_form view contains the TodoDoneCheckmark and remaining_days widgets", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "To-do",
        res_model: "project.task",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [false, "form"],
        ],
    });

    expect(".o_field_todo_done_checkmark").toHaveCount(3, {
        message: "The todo list view should contain 3 TodoDoneCheckmark widgets",
    });

    await contains(".o_data_cell").click();
    await animationFrame();
    expect(".o_field_remaining_days").toHaveCount(1, {
        message: "The todo form view should have deadline field (o_field_remaining_days)",
    });
});
