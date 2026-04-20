import { expect, test, beforeEach } from "@odoo/hoot";
import { click, queryAllTexts, waitFor } from "@odoo/hoot-dom";
import {
    mountView,
    contains,
    onRpc,
    toggleMenuItem,
    toggleActionMenu,
    clickSave,
    mockService,
    defineActions,
    getService,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";
import { WebClient } from "@web/webclient/webclient";

import { defineProjectModels, ProjectProject, ProjectTask } from "./project_models";

defineProjectModels();

beforeEach(() => {
    ProjectProject._records = [
        {
            id: 1,
            name: "Project 1",
            allow_milestones: false,
            allow_task_dependencies: false,
            allow_recurring_tasks: false,
        },
        {
            id: 2,
            name: "Project 2",
            allow_milestones: false,
            allow_task_dependencies: false,
            allow_recurring_tasks: false,
        },
    ];

    mockService("action", {
        doAction(actionRequest) {
            if (actionRequest === "reload_context") {
                expect.step("reload_context");
            } else {
                return super.doAction(...arguments);
            }
        },
    });
});

test("project.project (form)", async () => {
    await mountView({
        resModel: "project.project",
        resId: 1,
        type: "form",
        arch: `
            <form js_class="form_description_expander">
                <field name="name"/>
            </form>
        `,
    });
    expect(".o_form_view").toHaveCount(1);
});

const formViewParams = {
    resModel: "project.project",
    type: "form",
    actionMenus: {},
    resId: 1,
    arch: `
        <form js_class="project_project_form">
            <field name="active"/>
            <field name="name"/>
            <field name="allow_task_dependencies"/>
            <field name="allow_milestones"/>
            <field name="allow_recurring_tasks"/>
        </form>
    `,
};

onRpc("project.project", "check_features_enabled", ({ method }) => expect.step(method));

onRpc("web_save", ({ method }) => expect.step(method));

test("project.project (form) hide archive action for project user", async () => {
    onRpc("has_group", ({ args }) => args[1] === "project.group_project_user");
    await mountView(formViewParams);
    await toggleActionMenu();
    expect(`.o-dropdown--menu span:contains(Archive)`).toHaveCount(0, { message: "Archive action should not be visible" });
    expect.verifySteps(["check_features_enabled"]);
});

test("project.project (form) show archive action for project manager", async () => {
    onRpc("has_group", () => true);
    await mountView(formViewParams);
    await toggleActionMenu();
    expect(`.o-dropdown--menu span:contains(Archive)`).toHaveCount(1, { message: "Arhive action should be visible" });
    await toggleMenuItem("Archive");
    await contains(`.modal-footer .btn-primary`).click();
    await toggleActionMenu();
    expect(`.o-dropdown--menu span:contains(Unarchive)`).toHaveCount(1, { message: "Unarchive action should be visible" });
    await toggleMenuItem("UnArchive");
    expect.verifySteps(["check_features_enabled"]);
});

test("reload the page when allow_milestones is enabled on at least one project", async () => {
    // No project has allow_milestones enabled
    await mountView(formViewParams);

    await click("div[name='allow_milestones'] input");
    await clickSave();

    expect.verifySteps([
        "check_features_enabled",
        "web_save",
        "check_features_enabled",
        "reload_context",
    ]);
});

test("do not reload the page when allow_milestones is enabled and there already exists one project with the feature enabled", async () => {
    // Set a project with allow_milestones enabled
    ProjectProject._records[1].allow_milestones = true;
    await mountView(formViewParams);

    await click("div[name='allow_milestones'] input");
    await clickSave();

    // No reload should be triggered
    expect.verifySteps(["check_features_enabled", "web_save", "check_features_enabled"]);
});

test("reload the page when allow_milestones is disabled on all projects", async () => {
    // Set a project with allow_milestones enabled
    ProjectProject._records[0].allow_milestones = true;
    await mountView(formViewParams);

    await click("div[name='allow_milestones'] input");
    await clickSave();

    expect.verifySteps([
        "check_features_enabled",
        "web_save",
        "check_features_enabled",
        "reload_context",
    ]);
});

test("reload the page when allow_task_dependencies is enabled on at least one project", async () => {
    // No project has allow_task_dependencies enabled
    await mountView(formViewParams);

    await click("div[name='allow_task_dependencies'] input");
    await clickSave();

    expect.verifySteps([
        "check_features_enabled",
        "web_save",
        "check_features_enabled",
        "reload_context",
    ]);
});

test("do not reload the page when allow_task_dependencies is enabled and there already exists one project with the feature enabled", async () => {
    // Set a project with allow_task_dependencies enabled
    ProjectProject._records[1].allow_task_dependencies = true;
    await mountView(formViewParams);

    await click("div[name='allow_task_dependencies'] input");
    await clickSave();

    // No reload should be triggered
    expect.verifySteps(["check_features_enabled", "web_save", "check_features_enabled"]);
});

test("reload the page when allow_task_dependencies is disabled on all projects", async () => {
    // Set a project with allow_task_dependencies enabled
    ProjectProject._records[0].allow_task_dependencies = true;
    await mountView(formViewParams);

    await click("div[name='allow_task_dependencies'] input");
    await clickSave();

    expect.verifySteps([
        "check_features_enabled",
        "web_save",
        "check_features_enabled",
        "reload_context",
    ]);
});

test("reload the page when allow_recurring_tasks is enabled on at least one project", async () => {
    // No project has allow_recurring_tasks enabled
    await mountView(formViewParams);

    await click("div[name='allow_recurring_tasks'] input");
    await clickSave();

    expect.verifySteps([
        "check_features_enabled",
        "web_save",
        "check_features_enabled",
        "reload_context",
    ]);
});

test("do not reload the page when allow_recurring_tasks is enabled and there already exists one project with the feature enabled", async () => {
    // Set a project with allow_recurring_tasks enabled
    ProjectProject._records[1].allow_recurring_tasks = true;
    await mountView(formViewParams);

    await click("div[name='allow_recurring_tasks'] input");
    await clickSave();

    // No reload should be triggered
    expect.verifySteps(["check_features_enabled", "web_save", "check_features_enabled"]);
});

test("reload the page when allow_recurring_tasks is disabled on all projects", async () => {
    // Set a project with allow_recurring_tasks enabled
    ProjectProject._records[0].allow_recurring_tasks = true;
    await mountView(formViewParams);

    await click("div[name='allow_recurring_tasks'] input");
    await clickSave();

    expect.verifySteps([
        "check_features_enabled",
        "web_save",
        "check_features_enabled",
        "reload_context",
    ]);
});

test.tags("desktop");
test("project.project (form) display the top menu when opened from it", async () => {
    ProjectProject._views.form = formViewParams.arch;
    ProjectTask._views = {
        kanban: `<kanban><templates><t t-name="card"><field name="name"/></t></templates></kanban>`,
        search: `<search/>`,
    };
    defineActions([
        {
            id: 1,
            name: "Tasks",
            res_model: "project.task",
            views: [[false, "kanban"]],
        },
        {
            id: 2,
            name: "Overview",
            parent_res_model: "project.project",
            type: "ir.embedded.actions",
            parent_action_id: 1,
            python_method: "action_open_project_form",
        },
    ]);
    onRpc("project.project", "action_open_project_form", ({ args }) => ({
        type: "ir.actions.client",
        tag: "project_top_menu_overview",
        res_model: "project.project",
        res_id: args[0][0],
    }));
    // Overview is the first item of the top menu of the project
    user.updateUserSettings("id", 1);
    user.updateUserSettings("embedded_actions_config_ids", {
        "1+1": {
            embedded_actions_order: [2, false],
            embedded_actions_visibility: [2, false],
            embedded_visibility: true,
        },
    });
    await mountWithCleanup(WebClient);
    await getService("action").doActionButton({
        name: 1,
        type: "action",
        resId: 1,
        resModel: "project.project",
    });
    await waitFor(".o_form_view");
    expect(queryAllTexts(".o_embedded_actions > button > span")).toEqual(["Overview", "Tasks"]);
    expect(".o_embedded_actions > button.active").toHaveText("Overview");

    await contains(".o_embedded_actions > button:contains(Tasks)").click();
    expect(".o_kanban_view").toHaveCount(1);
    await contains(".o_embedded_actions > button:contains(Overview)").click();
    await waitFor(".o_form_view");
    expect(".o_embedded_actions > button.active").toHaveText("Overview");
    expect(".o_breadcrumb .breadcrumb-item").toHaveCount(0, {
        message: "switching between the top menu entries should not stack breadcrumbs",
    });
    expect.verifySteps(["check_features_enabled", "check_features_enabled"]);
});
