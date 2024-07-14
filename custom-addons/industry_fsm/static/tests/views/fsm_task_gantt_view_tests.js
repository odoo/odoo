/** @odoo-module */

import { getFixture, patchDate, click } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { servicesToDefineInGantt } from "@project_enterprise/../tests/task_gantt_dependency_tests";

const serviceRegistry = registry.category("services");

const ganttViewParams = {
    arch: '<gantt date_start="start_datetime" date_stop="date_deadline" js_class="task_gantt" />',
    resModel: "task",
    type: "gantt",
    context: {
        fsm_mode: true,
    },
    mockRPC(route, args) {
        if (args.method === "search_milestone_from_task") {
            return [];
        }
    },
};

let target;
QUnit.module("Views > TaskGanttView", {
    beforeEach() {
        patchDate(2024, 0, 3, 8, 0, 0);

        setupViewRegistries();

        target = getFixture();

        for (const service of servicesToDefineInGantt) {
            serviceRegistry.add(service, { start() {
                return {
                    formatter: () => { return ""; },
                };
            }});
        }

        ganttViewParams.serverData = {
            models: {
                task: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                        start_datetime: { string: "Start Date", type: "datetime" },
                        date_deadline: { string: "Start Date", type: "datetime" },
                        time: { string: "Time", type: "float" },
                        user_ids: {
                            string: "Assigned to",
                            type: "many2one",
                            relation: "res.users",
                        },
                        active: { string: "active", type: "boolean", default: true },
                        project_id: {
                            string: "Project",
                            type: "many2one",
                            relation: "project",
                        },
                    },
                    records: [],
                },
                "res.users": {
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
            views: {
                "task,false,form": 
                    `<form>
                        <field name="name"/>
                        <field name="start_datetime"/>
                        <field name="date_deadline"/>
                    </form>`,
                "task,false,list": '<tree><field name="name"/></tree>',
            }
        };
    },
});

QUnit.test(
    "fsm task gantt view",
    async (assert) => {
        const now = luxon.DateTime.now();

        await makeView(ganttViewParams);
        assert.containsOnce(target, ".o_gantt_view");
        await click(target, ".d-xl-inline-flex .o_gantt_button_add.btn-primary");
        assert.containsOnce(target, ".modal");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=start_datetime] .o_input").value,
            now.toFormat("MM/dd/yyyy 00:00:00"),
            "The fsm_mode present in the view context should set the start_datetime to the current day instead of the first day of the gantt view",
        );
    }
);
