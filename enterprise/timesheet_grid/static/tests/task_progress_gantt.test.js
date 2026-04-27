import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { defineModels, fields, models, onRpc } from "@web/../tests/web_test_helpers";
import { mountGanttView } from "@web_gantt/../tests/web_gantt_test_helpers";

class Task extends models.Model {
    name = fields.Char();
    start = fields.Datetime({ string: "Start Date" });
    stop = fields.Datetime({ string: "Stop Date" });
    progress = fields.Float();
    project_id = fields.Many2one({ relation: "project" });

    _records = [
        {
            id: 1,
            name: "Blop",
            start: "2020-06-14 08:00:00",
            stop: "2020-06-24 08:00:00",
            progress: 50.0,
            project_id: 1,
        },
        {
            id: 2,
            name: "Yop",
            start: "2020-06-02 08:00:00",
            stop: "2020-06-12 08:00:00",
            project_id: 1,
        },
    ];
}

class Project extends models.Model {
    name = fields.Char();
    _records = [{ id: 1, name: "My Project" }];
}

defineMailModels();
defineModels([Task, Project]);

test("Check progress bar values", async () => {
    mockDate("2020-06-12T08:00:00", +1);
    onRpc("get_all_deadlines", () => ({ milestone_id: [], project_id: [] }));
    await mountGanttView({
        resModel: "task",
        arch: `<gantt js_class="task_gantt" date_start="start" date_stop="stop" progress="progress"/>`,
    });
    const [firstPillFirstSpan, secondPillFirstSpan] = queryAll(".o_gantt_pill span:first-child");
    expect(firstPillFirstSpan).not.toHaveClass("o_gantt_progress");
    expect(secondPillFirstSpan).toHaveClass("o_gantt_progress");
    expect(secondPillFirstSpan.style.width).toBe("50%");
});
