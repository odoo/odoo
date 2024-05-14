import { describe, expect, test } from "@odoo/hoot";
import { contains, mountView, onRpc } from "@web/../tests/web_test_helpers";
import { defineProjectModels } from "@project/../tests/project_test_helpers";
import { start, startServer } from "@mail/../tests/mail_test_helpers";

describe.current.tags("desktop");
defineProjectModels();

test("Check whether subtask list functionality works as intended", async () => {
    const pyEnv = await startServer();
    const [projectId] = pyEnv["project.project"].create([
        { name: "Project One", active: true },
    ]);
    const [projectId2] = pyEnv["project.project"].create([
        { name: "Project Two", active: true },
    ]);
    const userId = pyEnv["res.users"].create([
        { name: "User One", login: "one", password: "one" },
    ]);
    const [taskId1, taskId2] = pyEnv["project.task"].create([
        { name: "task one", project_id: projectId, closed_subtask_count: 1, subtask_count: 4, state: "01_in_progress", user_ids: userId, priority: "0" },
        { name: "task five", project_id: projectId, closed_subtask_count: 1, subtask_count: 4, state: "01_in_progress", user_ids: userId, priority: "0" },
    ]);
    pyEnv["project.task"].create([
        { name: "task two", parent_id: taskId1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: "03_approved", priority: "0" },
        { name: "task three", parent_id: taskId1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: "02_changes_requested", priority: "0" },
        { name: "task four", parent_id: taskId1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: "1_done", priority: "0" },
        { name: "task six", parent_id: taskId2, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: "1_canceled", priority: "0" },
        { name: "task seven", parent_id: taskId1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: "01_in_progress", user_ids: userId, priority: "0" },
    ]);
    pyEnv["project.task"].create([
        { name: "task's Project Two", project_id: projectId2, child_ids: [], priority: "1" }
    ]);
    await start();
    await mountView({
        resModel: "project.task",
        type: "kanban",
    });

    expect(document.querySelector(".o_field_name_with_subtask_count")).toHaveText("task one (1/4 sub-tasks)");
    expect(".subtask_list").not.toBeDisplayed();

    await contains(".subtask_list_button").click();

    expect(".subtask_list").toBeDisplayed();
    expect(".subtask_list_row").toHaveCount(3);
    expect(document.querySelector(".o_field_name_with_subtask_count")).toHaveText("task one (1/4 sub-tasks)");
    expect(".subtask_state_widget_col").toHaveCount(3);
    expect(".subtask_user_widget_col").toHaveCount(3);
    expect(".subtask_name_col").toHaveCount(3);
    await contains(".subtask_list_button").click();
    expect(".subtask_list").not.toBeDisplayed();
});

test("Update closed subtask count in the kanban card when the state of a subtask is set to Done.", async () => {
    const pyEnv = await startServer();
    const [projectId] = pyEnv["project.project"].create([
        { name: "Project One", active: true },
    ]);
    const [projectId2] = pyEnv["project.project"].create([
        { name: "Project Two", active: true },
    ]);
    const userId = pyEnv["res.users"].create([
        { name: "User One", login: "one", password: "one" },
    ]);
    const [taskId1, taskId2] = pyEnv["project.task"].create([
        { name: "task one", project_id: projectId, closed_subtask_count: 1, subtask_count: 4, state: "01_in_progress", user_ids: userId, priority: "0" },
        { name: "task five", project_id: projectId, closed_subtask_count: 1, subtask_count: 4, state: "01_in_progress", user_ids: userId, priority: "0" },
    ]);
    pyEnv["project.task"].create([
        { name: "task two", parent_id: taskId1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: "03_approved", priority: "0" },
        { name: "task three", parent_id: taskId1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: "02_changes_requested", priority: "0" },
        { name: "task four", parent_id: taskId1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: "1_done", priority: "0" },
        { name: "task six", parent_id: taskId2, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: "1_canceled", priority: "0" },
        { name: "task seven", parent_id: taskId1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: "01_in_progress", user_ids: userId, priority: "0" },
    ]);
    pyEnv["project.task"].create([
        { name: "task's Project Two", project_id: projectId2, child_ids: [], priority: "1" }
    ]);

    onRpc("project.task", "web_read", () => {
        expect.step("web_read");
    });
    onRpc("project.task", "onchange", () => {
        expect.step("onchange");
    });
    onRpc("project.task", "web_save", () => {
        expect.step("web_save");
    });

    await start();
    await mountView({
        resModel: "project.task",
        type: "kanban",
    });

    expect(document.querySelector(".subtask_list_button")).toHaveText("1/4");
    await contains(".subtask_list_button").click();
    await contains(".o_field_widget.o_field_project_task_state_selection.subtask_state_widget_col .o_status:not(.o_status_green,.o_status_bubble)").click();
    expect(".o_field_widget.o_field_project_task_state_selection.subtask_state_widget_col .o_status:not(.o_status_green,.o_status_bubble)").not.toBeDisplayed();
    expect(["web_read", "onchange", "web_save"]).toVerifySteps();
});

test("Create a subtask from the kanban view", async () => {
    const pyEnv = await startServer();
    const [projectId] = pyEnv["project.project"].create([
        { name: "Project One", active: true },
    ]);
    const [projectId2] = pyEnv["project.project"].create([
        { name: "Project Two", active: true },
    ]);
    const userId = pyEnv["res.users"].create([
        { name: "User One", login: "one", password: "one" },
    ]);
    const [taskId1, taskId2] = pyEnv["project.task"].create([
        { name: "task one", project_id: projectId, closed_subtask_count: 1, subtask_count: 4, state: "01_in_progress", user_ids: userId, priority: "0" },
        { name: "task five", project_id: projectId, closed_subtask_count: 1, subtask_count: 4, state: "01_in_progress", user_ids: userId, priority: "0" },
    ]);
    pyEnv["project.task"].create([
        { name: "task two", parent_id: taskId1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: "03_approved", priority: "0" },
        { name: "task three", parent_id: taskId1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: "02_changes_requested", priority: "0" },
        { name: "task four", parent_id: taskId1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: "1_done", priority: "0" },
        { name: "task six", parent_id: taskId2, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: "1_canceled", priority: "0" },
        { name: "task seven", parent_id: taskId1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: "01_in_progress", user_ids: userId, priority: "0" },
    ]);
    pyEnv["project.task"].create([
        { name: "task's Project Two", project_id: projectId2, child_ids: [], priority: "1" }
    ]);
    onRpc("project.task", "create", ({ args }) => {
        const [{ display_name, parent_id }] = args[0];
        expect(display_name).toBe("foo");
        expect(parent_id).toBe(taskId1);
        expect.step("create");
    });
    onRpc("project.task", "web_read", () => {
        expect.step("web_read");
    });
    await start();
    await mountView({
        resModel: "project.task",
        type: "kanban",
    });
    expect(document.querySelector(".subtask_list_button")).toHaveText("1/4");
    await contains(".subtask_list_button").click();
    await contains(".subtask_create").click();
    await contains(".subtask_create_input input").fill("foo");
    expect(".subtask_list_row").toHaveCount(4);
    expect(["web_read", "create", "web_read"]).toVerifySteps();
});

test("Check that the sub task of another project can be added", async () => {
    const pyEnv = await startServer();
    const [projectId] = pyEnv["project.project"].create([
        { name: "Project One", active: true },
    ]);
    const [taskId] = pyEnv["project.task"].create([
        { name: "task's Project Two", project_id: projectId, child_ids: [], priority: "1" }
    ]);
    await start();
    await mountView({
        resModel: "project.task",
        type: "form",
        resId: taskId
    });
    await contains(".o_field_x2many_list_row_add a").click();
    await contains("[name='project_id'] .dropdown input").click();
    await contains("[name='project_id'] .dropdown .dropdown-menu li:nth-child(2)").click();
    await contains(".o_data_row > td[name='name'] > div > input").fill("aaa");
    await contains(".o_form_button_save").click();
    expect(".o_field_project").toHaveText("Project One");
});

test("focus new subtask's name", async () => {
    await mountView({
        resModel: "project.task",
        type: "form",
    });

    await contains(".o_field_x2many_list_row_add a").click();
    expect(document.activeElement).toBe(document.querySelector(".o_data_row > td[name='name'] > div > input"));
});
