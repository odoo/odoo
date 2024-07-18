import { expect, test, beforeEach } from "@odoo/hoot";
import { queryAllTexts, queryFirst } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import { WebClient } from "@web/webclient/webclient";
import {
    mountView,
    contains,
    onRpc,
    mountWithCleanup,
    getService,
} from "@web/../tests/web_test_helpers";

import { defineTodoModels } from "./todo_test_helpers";
import { ProjectTask } from "./mock_server/mock_models/project_task";

defineTodoModels();

beforeEach(() => {
    ProjectTask._views = {
        list: `
            <tree js_class="todo_list">
                <field name="name" nolabel="1"/>
                <field name="state" widget="todo_done_checkmark" nolabel="1"/>
            </tree>`,
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

test.skip("Check that todo_form view contains the TodoDoneCheckmark and TodoEditableBreadcrumbName widgets", async () => {
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

    await contains(queryFirst(".o_data_cell")).click();
    await animationFrame();
    expect(".o_todo_breadcrumb_name_input").toHaveCount(1, {
        message: "The todo should have the appropriate class for TodoEditableBreadcrumbName",
    });

    expect(".o_todo_done_button").toHaveCount(1, {
        message: "The todo should have the appropriate class TodoDoneCheckmark",
    });
});
