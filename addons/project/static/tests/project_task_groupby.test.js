import { describe, expect, test } from "@odoo/hoot";
import { mountView } from "@web/../tests/web_test_helpers";
import { defineProjectModels } from "@project/../tests/project_test_helpers";
import { start, startServer } from "@mail/../tests/mail_test_helpers";

describe.current.tags("desktop");
defineProjectModels();

test("Test group label for empty project in tree", async () => {
    const pyEnv = await startServer();
    pyEnv["project.task"].create({
        active: true,
        display_name: "My task",
        project_id: false,
        user_ids: [],
        date_deadline: false,
    });
    await start();
    await mountView({
        resModel: "project.task",
        type: "list",
        arch: `<tree js_class="project_task_list"/>`,
        searchViewArch: `
            <search string="">
                <filter string="Project" name="project" context="{'group_by': 'project_id'}" />
            </search>`,
        context: { search_default_project: 1 },
    });
    expect(".o_group_name").toHaveText("🔒 Private (1)");
});

test("Test group label for empty assignees in tree", async () => {
    const pyEnv = await startServer();
    pyEnv["project.task"].create({
        active: true,
        display_name: "My task",
        project_id: false,
        user_ids: [],
        date_deadline: false,
    });
    await start();
    await mountView({
        resModel: "project.task",
        type: "list",
        arch: `<tree js_class="project_task_list"/>`,
        searchViewArch: `
            <search string="">
                <filter string="Unassigned" name="user_ids" context="{'group_by': 'user_ids'}" />
            </search>`,
        context: { search_default_user_ids: 1 },
    });
    expect(".o_group_name").toHaveText("👤 Unassigned (1)");
});

test("Test group label for empty deadline in tree", async () => {
    const pyEnv = await startServer();
    pyEnv["project.task"].create({
        active: true,
        display_name: "My task",
        project_id: false,
        user_ids: [],
        date_deadline: false,
    });
    await start();
    await mountView({
        resModel: "project.task",
        type: "list",
        arch: `<tree js_class="project_task_list"/>`,
        searchViewArch: `
            <search string="">
                <filter string="date_deadline" name="date_deadline" context="{'group_by': 'date_deadline'}" />
            </search>`,
        context: { search_default_date_deadline: 1 },
    });
    expect(".o_group_name").toHaveText("None (1)");
});

test("Test group label for empty project in kanban", async () => {
    const pyEnv = await startServer();
    pyEnv["project.task"].create({
        active: true,
        display_name: "My task",
        project_id: false,
        user_ids: [],
        date_deadline: false,
    });
    await start();
    await mountView({
        resModel: "project.task",
        type: "kanban",
        arch: `
            <kanban js_class="project_task_kanban" default_group_by="project_id">
                <templates>
                    <t t-name="kanban-box"/>
                </templates>
            </kanban>`
    });
    expect(".o_column_title").toHaveText("🔒 Private\n1");
});

test("Test group label for empty assignees in kanban", async () => {
    const pyEnv = await startServer();
    pyEnv["project.task"].create({
        active: true,
        display_name: "My task",
        project_id: false,
        user_ids: [],
        date_deadline: false,
    });
    await start();
    await mountView({
        resModel: "project.task",
        type: "kanban",
        arch: `
            <kanban js_class="project_task_kanban" default_group_by="user_ids">
                <templates>
                    <t t-name="kanban-box"/>
                </templates>
            </kanban>`
    });
    expect(".o_column_title").toHaveText("👤 Unassigned\n1");
});

test("Test group label for empty deadline in kanban", async () => {
    const pyEnv = await startServer();
    pyEnv["project.task"].create({
        active: true,
        display_name: "My task",
        project_id: false,
        user_ids: [],
        date_deadline: false,
    });
    await start();
    await mountView({
        resModel: "project.task",
        type: "kanban",
        arch: `
            <kanban js_class="project_task_kanban" default_group_by="date_deadline">
                <templates>
                    <t t-name="kanban-box"/>
                </templates>
            </kanban>`
    });
    expect(".o_column_title").toHaveText("None");
});

test("Test group label for empty project in pivot", async () => {
    const pyEnv = await startServer();
    pyEnv["project.task"].create({
        active: true,
        display_name: "My task",
        project_id: false,
        user_ids: [],
        date_deadline: false,
    });
    await start();
    await mountView({
        resModel: "project.task",
        type: "pivot",
        arch: `
            <pivot js_class="project_pivot">
                <field name="project_id" type="row" />
            </pivot>`
    });
    expect("tr:nth-of-type(2) .o_pivot_header_cell_closed").toHaveText("Private");
});

test("Test group label for empty assignees in pivot", async () => {
    const pyEnv = await startServer();
    pyEnv["project.task"].create({
        active: true,
        display_name: "My task",
        project_id: false,
        user_ids: [],
        date_deadline: false,
    });
    await start();
    await mountView({
        resModel: "project.task",
        type: "pivot",
        arch: `
            <pivot js_class="project_pivot">
                <field name="user_ids" type="row" />
            </pivot>`
    });
    expect("tr:nth-of-type(2) .o_pivot_header_cell_closed").toHaveText("Unassigned");
});

test("Test group label for empty deadline in pivot", async () => {
    const pyEnv = await startServer();
    pyEnv["project.task"].create({
        active: true,
        display_name: "My task",
        project_id: false,
        user_ids: [],
        date_deadline: false,
    });
    await start();
    await mountView({
        resModel: "project.task",
        type: "pivot",
        arch: `
            <pivot js_class="project_pivot">
                <field name="date_deadline" type="row" />
            </pivot>`
    });
    expect("tr:nth-of-type(2) .o_pivot_header_cell_closed").toHaveText("None");
});
