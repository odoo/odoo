import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";

import { WebClient } from "@web/webclient/webclient";
import { clickOnDataset, setupChartJsForTests } from "@web/../tests/views/graph/graph_test_helpers";
import {
    contains,
    fields,
    getService,
    mockService,
    models,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";

import { defineProjectModels, projectModels } from "./project_models";

describe.current.tags("desktop");

class ReportProjectTaskUser extends models.Model {
    _name = "report.project.task.user";
    project_id = fields.Many2one({ relation: "project.project" });
    display_in_project = fields.Boolean();
    task_id = fields.Many2one({ relation: "project.task" });
    nbr = fields.Integer({ string: "# of Tasks" });

    _records = [
        { id: 4, project_id: 1, display_in_project: true },
        { id: 6, project_id: 1, display_in_project: true },
        { id: 9, project_id: 2, display_in_project: true },
    ];
    _views = {
        graph: /* xml */ `
            <graph string="Tasks Analysis" sample="1" js_class="project_task_analysis_graph">
                <field name="project_id"/>
            </graph>
        `,
        pivot: /* xml */ `
            <pivot string="Tasks Analysis" display_quantity="1" sample="1" js_class="project_task_analysis_pivot">
                <field name="project_id"/>
            </pivot>
        `,
    };
}
projectModels.ReportProjectTaskUser = ReportProjectTaskUser;
projectModels.ProjectTask._views = {
    form: /* xml */ `<form><field name="name"/></form>`,
    list: /* xml */ `<list><field name="name"/></list>`,
    search: /* xml */ `<search><field name="name"/></search>`,
};
defineProjectModels();
setupChartJsForTests();

async function mountView(viewName, ctx = {}) {
    const view = await mountWithCleanup(WebClient);
    await getService("action").doAction({
        id: 1,
        name: "tasks analysis",
        res_model: "report.project.task.user",
        type: "ir.actions.act_window",
        views: [[false, viewName]],
        context: ctx,
    });
    return view;
}

test("report.project.task.user (graph): clicking on a bar leads to project.task list", async () => {
    mockService("action", {
        doAction({ res_model }) {
            expect.step(res_model);
            return super.doAction(...arguments);
        },
    });

    const view = await mountView("graph");
    await animationFrame();
    await clickOnDataset(view);
    await animationFrame();

    expect(".o_list_renderer").toBeDisplayed({
        message: "Clicking on a bar should open a list view",
    });
    // The model of the list view that is opened consequently should be "project.task"
    expect.verifySteps(["report.project.task.user", "project.task"]);
});

test("report.project.task.user (pivot): clicking on a cell leads to project.task list", async () => {
    mockService("action", {
        doAction({ res_model }) {
            expect.step(res_model);
            return super.doAction(...arguments);
        },
    });

    await mountView("pivot");
    await animationFrame();
    await contains(".o_pivot_cell_value").click();
    await animationFrame();

    expect(".o_list_renderer").toBeDisplayed({
        message: "Clicking on a cell should open a list view",
    });
    // The model of the list view that is opened consequently should be "project.task"
    expect.verifySteps(["report.project.task.user", "project.task"]);
});

test("report.project.task.user: fix the domain, in case field is not present in main model", async () => {
    mockService("action", {
        doAction({ domain, res_model }) {
            if (res_model === "project.task") {
                expect(domain).toEqual(["&", ["display_in_project", "=", true], "&", [1, "=", 1], ["id", "=", 1]]);
            }
            return super.doAction(...arguments);
        },
    });

    ReportProjectTaskUser._records = [
        { id: 1, nbr: 1, task_id: 1, display_in_project: true },
        { id: 2, nbr: 1, task_id: 2, display_in_project: true },
    ];
    ReportProjectTaskUser._views = {
        graph: /* xml */ `
            <graph string="Tasks Analysis" sample="1" js_class="project_task_analysis_graph">
                <field name="task_id"/>
                <field name="nbr"/>
            </graph>
        `
    };

    const view = await mountView("graph", { group_by: ["task_id", "nbr"] });
    await animationFrame();
    await clickOnDataset(view);
    await animationFrame();
    expect(`.o_list_renderer .o_data_row`).toHaveCount(1);
});
