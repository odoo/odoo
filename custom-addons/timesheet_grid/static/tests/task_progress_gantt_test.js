/** @odoo-module **/

import { getFixture, patchDate } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { servicesToDefineInGantt } from "@project_enterprise/../tests/task_gantt_dependency_tests";

servicesToDefineInGantt.push("timesheet_uom");
const serviceRegistry = registry.category("services");

let serverData;
let target;
QUnit.module("Views > GanttView > TaskGantt", {
    beforeEach() {
        patchDate(2020, 5, 22, 8, 0, 0);
        setupViewRegistries();
        target = getFixture();
        for (const service of servicesToDefineInGantt) {
            serviceRegistry.add(service, { start() {} });
        }
        serverData = {
            models: {
                task: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                        progress: { string: "progress", type: "float" },
                        start: { string: "Start Date", type: "datetime" },
                        stop: { string: "Start Date", type: "datetime" },
                        user_id: { string: "Assigned to", type: "many2one", relation: "users" },
                        allow_timesheets: { string: "Allow timeshet", type: "boolean" },
                        project_id: {
                            string: "Project",
                            type: "many2one",
                            relation: "project",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            name: "Blop",
                            start: "2020-06-14 08:00:00",
                            stop: "2020-06-24 08:00:00",
                            user_id: 100,
                            progress: 50.00,
                            allow_timesheets: true,
                            project_id: 1,
                        },
                        {
                            id: 2,
                            name: "Yop",
                            start: "2020-06-02 08:00:00",
                            stop: "2020-06-12 08:00:00",
                            user_id: 101, progress: 0,
                            allow_timesheets: true,
                            project_id: 1,
                        },
                    ],
                },
                users: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                    },
                    records: [
                        { id: 100, name: "Jane Doe" },
                        { id: 101, name: "John Doe" },
                    ],
                },
                project: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                    },
                    records: [{ id: 1, name: "My Project" }],
                },
            },
        };
    },
});

QUnit.test("Check progress bar values", async (assert) => {
    await makeView({
        arch: `<gantt js_class="task_gantt" date_start="start" date_stop="stop" progress="progress"/>`,
        resModel: "task",
        type: "gantt",
        serverData,
        async mockRPC(_, args) {
            if (args.method === "search_milestone_from_task") {
                return [];
            }
        }
    })
    const [firstPill, secondPill] = target.querySelectorAll(".o_gantt_pill");
    assert.containsNone(firstPill, "span.o_gantt_progress");
    assert.containsOnce(secondPill, "span.o_gantt_progress");
    assert.strictEqual(secondPill.querySelector("span").getAttribute('style'), "width:50%;");
});
