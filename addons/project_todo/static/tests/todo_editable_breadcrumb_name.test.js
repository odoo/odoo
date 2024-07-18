import { test, expect, describe, beforeEach } from "@odoo/hoot";
import { queryOne, queryFirst } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import { WebClient } from "@web/webclient/webclient";
import {
    onRpc,
    contains,
    mountWithCleanup,
    getService,
    clickSave,
} from "@web/../tests/web_test_helpers";

import { click } from "@mail/../tests/mail_test_helpers";

import { defineTodoModels } from "./todo_test_helpers";
import { ProjectTask } from "./mock_server/mock_models/project_task";

describe.current.skip();

describe.current.tags("desktop");
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
                <field name="state" invisible="1"/>
            </form>`,
        search: `
            <search/>`,
    };
});

test("Check changing TodoEditableBreadcrumbName input by a custom input in form view", async () => {
    onRpc("web_save", ({ args }) => {
        expect(args[1].name).toBe("Todo 42", {
            message: "The todo name should be updated",
        });
        expect.step("web_save");
    });

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
    const breadcrumbNameInput = queryOne(".o_todo_breadcrumb_name_input");
    expect(breadcrumbNameInput).toHaveClass("o_todo_breadcrumb_name_input", {
        message: "The todo should have the appropriate class",
    });
    expect(breadcrumbNameInput.value).toBe("Todo 1");
    await contains(breadcrumbNameInput).edit("Todo 42");
    click(breadcrumbNameInput);
    expect(breadcrumbNameInput).not.toHaveClass("o-todo-untitled", {
        message: "The todo should not be untitled",
    });
    await clickSave();
    await animationFrame();
    expect.verifySteps(["web_save"]);
});

test("Check changing TodoEditableBreadcrumbName input by a empty input in form view", async () => {
    onRpc("web_save", ({ args }) => {
        expect(args[1].name).toBe("Untitled to-do", {
            message: "The todo name should be untitled",
        });
        expect.step("web_save");
    });

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
    const breadcrumbNameInput = queryOne(".o_todo_breadcrumb_name_input");
    await contains(breadcrumbNameInput).edit("");
    click(breadcrumbNameInput);
    expect(breadcrumbNameInput.value).toBe(breadcrumbNameInput.placeholder);

    expect(breadcrumbNameInput).toHaveClass("o-todo-untitled", {
        message: "The todo should be untitled",
    });
    await clickSave();
    await animationFrame();
    expect.verifySteps(["web_save"]);
});

test("Check changing TodoEditableBreadcrumbName input by the placeholder in form view", async () => {
    onRpc("web_save", ({ args }) => {
        expect(args[1].name).toBe("Untitled to-do", {
            message: "The todo name should be untitled",
        });
        expect.step("web_save");
    });

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
    const breadcrumbNameInput = queryOne(".o_todo_breadcrumb_name_input");
    await contains(breadcrumbNameInput).edit(breadcrumbNameInput.placeholder);
    click(breadcrumbNameInput);
    expect(breadcrumbNameInput.value).toBe(breadcrumbNameInput.placeholder);

    expect(breadcrumbNameInput).toHaveClass("o-todo-untitled", {
        message: "The todo should be untitled",
    });
    await clickSave();
    await animationFrame();
    expect.verifySteps(["web_save"]);
});
