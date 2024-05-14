import { describe, expect, test } from "@odoo/hoot";
import { contains, mountView, onRpc } from "@web/../tests/web_test_helpers";
import { defineProjectModels } from "@project/../tests/project_test_helpers";
import { startServer } from "@mail/../tests/mail_test_helpers";

describe.current.tags("desktop");
defineProjectModels();

test("quick create button is visible when the user has access rights.", async () => {
    const pyEnv = await startServer();
    const [projectId] = pyEnv['project.project'].create([
        { name: "Project One" },
    ]);
    const [stageId] = pyEnv['project.task.type'].create([
        { name: "New" },
    ]);
    pyEnv['project.task'].create([
        { name: 'task one', project_id: projectId, stage_id: stageId },
    ]);
    await mountView({
        type: "kanban",
        resModel: "project.task",
        arch: `
            <kanban js_class="project_task_kanban">
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="name"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        searchViewArch: `
            <search string="">
                <filter string="stage" name="stage_id" context="{'group_by': 'stage_id'}" />
            </search>`,
        context: {
            active_model: "project.project",
            default_project_id: projectId,
            search_default_stage_id: 1
        },
    });
    expect(".o_column_quick_create").toBeDisplayed();
    await contains(".o_kanban_add_column").click();
});

test("quick create button is not visible when the user not have access rights.", async () => {
    const pyEnv = await startServer();
    const [projectId] = pyEnv['project.project'].create([
        { name: "Project One" },
    ]);
    const [stageId] = pyEnv['project.task.type'].create([
        { name: "New" },
    ]);
    pyEnv['project.task'].create([
        { name: 'task one', project_id: projectId, stage_id: stageId },
    ]);
    onRpc("has_group", () => false);
    await mountView({
        type: "kanban",
        resModel: "project.task",
        arch: `
            <kanban js_class="project_task_kanban">
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="name"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        searchViewArch: `
            <search string="">
                <filter string="stage" name="stage_id" context="{'group_by': 'stage_id'}" />
            </search>`,
        context: {
            active_model: "project.project",
            default_project_id: projectId,
            search_default_stage_id: 1
        },
    });

    expect(".o_column_quick_create").not.toBeDisplayed();
});
