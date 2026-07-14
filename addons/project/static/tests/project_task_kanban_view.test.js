import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, edit } from "@odoo/hoot-dom";

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
    `;
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

test("shadow stages should be displayed in the project Kanban", async () => {
    await mountView({
        resModel: "project.task",
        type: "kanban",
        context: {
            active_model: "project.task.type.delete.wizard",
            default_project_id: 1,
        },
    });

    expect(".o_kanban_header").toHaveCount(1);
    expect(".o_kanban_example_background_container").toHaveCount(1);
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
    onRpc("web_read_group", () => {
        return {
            groups: [{ stage_id: [1, "Stage 1"] }],
            length: 1,
        };
    });
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
