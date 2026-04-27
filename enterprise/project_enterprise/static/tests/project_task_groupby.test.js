import { beforeEach, expect, test, describe } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { queryOne } from "@odoo/hoot-dom";
import { defineProjectModels } from "@project/../tests/project_models";
import { ProjectTask } from "@project_enterprise/../tests/task_gant_model";
import { mountView, onRpc } from "@web/../tests/web_test_helpers";
import { mountGanttView } from "@web_gantt/../tests/web_gantt_test_helpers";

defineProjectModels();
describe.current.tags("desktop");

beforeEach(() => {
    mockDate("2021-02-12 00:00:00");
    ProjectTask._records = [
        {
            id: 1,
            display_name: "My Task",
            project_id: false,
            start: "2021-02-01",
            stop: "2021-02-02",
            partner_id: false,
        },
    ];
});

test("Test group label for empty project in gantt", async () => {
    onRpc("project.task", "get_all_deadlines", () => {
        return { milestone_id: [], project_id: [] };
    });
    await mountGanttView({
        type: "gantt",
        resModel: "project.task",
        arch: `<gantt
                    js_class="task_gantt"
                    date_start="start"
                    date_stop="stop"
                />`,
        groupBy: ["project_id"],
    });
    expect(queryOne(".o_gantt_row_title")).toHaveText("🔒 Private");
});

test("Test group label for empty project in map", async () => {
    await mountView({
        type: "map",
        resModel: "project.task",
        arch: `<map js_class="project_task_map" res_partner="partner_id"/>`,
        groupBy: ["project_id"],
    });
    expect(queryOne(".o-map-renderer--pin-list-group-header")).toHaveText("Private");
});
