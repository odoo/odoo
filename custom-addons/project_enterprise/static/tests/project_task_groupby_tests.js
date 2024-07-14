/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { getFixture, patchDate } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { start } from "@mail/../tests/helpers/test_utils";

let target;

QUnit.module("Project", (hooks) => {
    hooks.beforeEach(async () => {
        const pyEnv = await startServer();
        pyEnv.mockServer.models["project.task"] = {
            fields: {
                id: { string: "Id", type: "integer" },
                display_name: { string: "Name", type: "char" },
                project_id: {
                    string: "Project",
                    type: "many2one",
                    relation: "project.project",
                },
                start: { string: "Start Date", type: "datetime" },
                stop: { string: "Stop Date", type: "datetime" },
                partner_id: {
                    string: "Customer",
                    type: "many2one",
                    relation: "res.partner",
                },
            },
            records: [
                {
                    id: 1,
                    display_name: "My task",
                    project_id: false,
                    start: "2021-02-01",
                    stop: "2021-02-02",
                    partner_id: false,
                },
            ],
        };
        patchDate(2021, 1, 1, 12, 0, 0);
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.test("Test group label for empty project in gantt", async function (assert) {
        assert.expect(1);

        const views = {
            "project.task,false,gantt": `<gantt
                    js_class="task_gantt"
                    date_start="start"
                    date_stop="stop"
                />`,
        };
        const { openView } = await start({
            serverData: { views },
            mockRPC: function (route, args) {
                if (args.method === "search_milestone_from_task") {
                    return [];
                }
            },
        });
        await openView({
            res_model: "project.task",
            views: [[false, "gantt"]],
            context: { group_by: ["project_id"] },
        });

        assert.strictEqual(target.querySelector(".o_gantt_row_title").innerText, "🔒 Private");
    });

    QUnit.test("Test group label for empty project in map", async function (assert) {
        assert.expect(1);

        const views = {
            "project.task,false,map": `<map js_class="project_task_map" res_partner="partner_id"/>`,
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: "project.task",
            views: [[false, "map"]],
            context: { group_by: ["project_id"] },
        });

        assert.strictEqual(
            target.querySelector(".o-map-renderer--pin-list-group-header").innerText,
            "Private"
        );
    });
});
