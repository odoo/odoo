import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, edit, waitFor } from "@odoo/hoot-dom";
import {
    contains,
    fields,
    models,
    mountView,
    onRpc,
    toggleKanbanColumnActions,
} from "@web/../tests/web_test_helpers";

import { defineProjectModels, projectModels } from "./project_models";

class ProjectTaskTypeDeleteWizard extends models.Model {
    _name = "project.task.type.delete.wizard";

    task_count = fields.Integer({ string: "Number of tasks" });
    stages_active = fields.Boolean();
    project_ids = fields.Many2many({ string: "Projects", relation: "project.project" });
    stage_ids = fields.Many2many({ string: "Stages to delete", relation: "project.task.type" });

    _views = {
        form: `
            <form string="Delete Stage">
                <footer>
                    <button string="Delete" type="object" name="action_unlink" class="btn btn-primary"/>
                    <button string="Discard" special="cancel"/>
                </footer>
            </form>
        `,
    };
}
projectModels.ProjectTaskTypeDeleteWizard = ProjectTaskTypeDeleteWizard;

defineProjectModels();
describe.current.tags("desktop");

beforeEach(() => {
    projectModels.ProjectTask._records = [];
    projectModels.ProjectTask._views.kanban = `
        <kanban default_group_by="stage_id" js_class="project_task_kanban">
            <templates>
                <t t-name="card">
                    <field name="name"/>
                </t>
            </templates>
        </kanban>
    `,
    onRpc(({ method }) => {
        if (method === "unlink_wizard") {
            return {
                type: "ir.actions.act_window",
                name: "Delete Stage",
                res_model: "project.task.type.delete.wizard",
                view_mode: "form",
                views: [[false, "form"]],
                target: "new",
                res_id: 1,
            };
        } else if (method === "action_unlink") {
            return {
                type: "ir.actions.act_window_close",
                infos: {
                    success: true,
                },
            };
        }
    });
});

test("stages nocontent helper should be displayed in the project Kanban", async () => {
    await mountView({
        resModel: "project.task",
        type: "kanban",
        context: {
            active_model: "project.task.type.delete.wizard",
            default_project_id: 1,
        },
    });

    expect(".o_kanban_header").toHaveCount(1);
    expect(".o_kanban_stages_nocontent").toHaveCount(1);
});

test("quick create button is visible when the user has access rights.", async () => {
    onRpc("has_group", () => true);
    await mountView({
        resModel: "project.task",
        type: "kanban",
        context: {
            active_model: "project.project",
            default_project_id: 1,
        },
    });
    await animationFrame();
    expect(".o_column_quick_create").toHaveCount(1);
});

test("quick create button is not visible when the user not have access rights", async () => {
    onRpc("has_group", () => false);
    await mountView({
        resModel: "project.task",
        type: "kanban",
        context: {
            active_model: "project.project",
            default_project_id: 1,
        },
    });
    await animationFrame();
    expect(".o_column_quick_create").toHaveCount(0);
});

test("project.task (kanban): toggle sub-tasks", async () => {
    projectModels.ProjectTask._records = [
        {
            id: 1,
            project_id: 1,
            name: "Task 1",
            stage_id:  1,
            display_in_project: true,
        },
        {
            id: 2,
            project_id: 1,
            name: "Task 2",
            stage_id:  1,
            display_in_project: false,
        }
    ];
    await mountView({
        resModel: "project.task",
        type: "kanban",
        context: {
            active_model: "project.project",
            default_project_id: 1,
        },
    });
    expect(".o_kanban_record").toHaveCount(1);
    expect(".o_control_panel_navigation button i.fa-sliders").toHaveCount(1);
    await click(".o_control_panel_navigation button i.fa-sliders");
    await waitFor("span.o-dropdown-item");
    expect("span.o-dropdown-item").toHaveText("Show Sub-Tasks");
    await click("span.o-dropdown-item");
    await animationFrame();
    expect(".o_kanban_record").toHaveCount(2);
});

test("delete just created stage", async () => {
    await mountView({
        resModel: "project.task",
        type: "kanban",
        context: {
            active_model: "project.project",
            default_project_id: 1,
        },
    });

    await contains(".o_column_quick_create input").click();
    await edit("Stage 1");
    await contains(".o_kanban_add").click();

    let clickColumnAction = await toggleKanbanColumnActions(0);
    await clickColumnAction("Delete");
    await click("button[special=cancel]");
    expect(".o_column_title").toHaveCount(1, {
        message: "The stage should not have been deleted.",
    });

    clickColumnAction = await toggleKanbanColumnActions(0);
    await clickColumnAction("Delete");
    await click("button[name=action_unlink]");
    await animationFrame();
    expect(".o_column_title").toHaveCount(0, { message: "The stage should have been deleted." });
});

test("delete existing stage", async () => {
    onRpc("web_read_group", () => ({
        groups: [{
            stage_id: [1, "Stage 1"],
            __records: [],
        }],
        length: 1,
    }));
    await mountView({
        resModel: "project.task",
        type: "kanban",
        context: {
            active_model: "project.project",
            default_project_id: 1,
        },
    });

    let clickColumnAction = await toggleKanbanColumnActions(0);
    await clickColumnAction("Delete");
    await click("button[special=cancel]");
    expect(".o_column_title").toHaveCount(1, {
        message: "The stage should not have been deleted.",
    });

    clickColumnAction = await toggleKanbanColumnActions(0);
    await clickColumnAction("Delete");
    await click("button[name=action_unlink]");
    await animationFrame();
    expect(".o_column_title").toHaveCount(0, { mesage: "The stage should have been deleted." });
});
