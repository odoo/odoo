import { describe, test } from "@odoo/hoot";
import { mountView } from "@web/../tests/web_test_helpers";
import { defineProjectModels } from "@project/../tests/project_test_helpers";
import { startServer } from "@mail/../tests/mail_test_helpers";
import { checkLabels, checkLegend, selectMode } from "@web/../tests/views/graph/graph_test_helpers";

describe.current.tags("desktop");
defineProjectModels();

test("check custom default label", async () => {
    const pyEnv = await startServer();
    const [projectId] = pyEnv["project.project"].create([{ name: "Project 1" }]);
    pyEnv["project.task"].create([
        { name: "Task 1", project_id: projectId },
        { name: "Task 2", project_id: false },
    ]);
    const view = await mountView({
        type: "graph",
        resModel: "project.task",
        arch: `
            <graph js_class="project_task_graph">
                <field name="project_id"/>
            </graph>`,
    });
    checkLabels(view, ["Project 1", "🔒 Private"]);
    checkLegend(view, ["Count"]);
    await selectMode("line");
    checkLabels(view, ["", "Project 1", ""]);
    checkLegend(view, ["Count"]);
    await selectMode("pie");
    checkLabels(view, ["Project 1", "🔒 Private"]);
    checkLegend(view, ["Project 1", "🔒 Private"]);
});

test("check default label with 2 fields in groupby", async () => {
    const pyEnv = await startServer();
    const [projectId] = pyEnv["project.project"].create([{ name: "Project 1" }]);
    const [milestoneId] = pyEnv["project.milestone"].create([{ name: "Milestone 1" }]);
    pyEnv["project.task"].create([
        { name: "Task 1", project_id: projectId, milestone_id: milestoneId },
        { name: "Task 2", project_id: false, milestone_id: false },
    ]);
    const view = await mountView({
        type: "graph",
        resModel: "project.task",
        arch: `
            <graph js_class="project_task_graph">
                <field name="project_id"/>
                <field name="milestone_id"/>
            </graph>
`,
    });
    checkLabels(view, ["Project 1", "🔒 Private"]);
    checkLegend(view, ["Milestone 1", "None", "Sum"]);
    await selectMode("line");
    checkLabels(view, ["", "Project 1", ""]);
    checkLegend(view, ["Milestone 1"]);
    await selectMode("pie");
    checkLabels(view, [
        "Project 1 / Milestone 1",
        "🔒 Private / None",
    ]);
    checkLegend(view, [
        "Project 1 / Milestone 1",
        "🔒 Private / None",
    ]);
});
