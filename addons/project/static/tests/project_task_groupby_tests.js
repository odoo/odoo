/** @odoo-module */

import { getFixture } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { start, startServer } from "@mail/../tests/helpers/test_utils";

let target;

QUnit.module("Project", (hooks) => {
    hooks.beforeEach(async () => {
        const pyEnv = await startServer();
        pyEnv.mockServer.models['project.task'] = {
            fields: {
                id: { string: "Id", type: "integer" },
                display_name: { string: "Name", type: "char" },
                project_id: {
                    string: "Project",
                    type: "many2one",
                    relation: "project.project",
                },
            },
            records: [{
                id: 1,
                display_name: "My task",
                project_id: false,
            }],
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.test("Test group label for empty project in tree", async function (assert) {
        assert.expect(1);

        const views = {
            "project.task,false,list":
                `<tree js_class="project_task_list"/>`,
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: "project.task",
            views: [[false, "tree"]],
            context: { group_by: ["project_id"] },
        });

        assert.strictEqual(target.querySelector(".o_group_name").innerText, "🔒 Private (1)");
    });

    QUnit.test("Test group label for empty project in kanban", async function (assert) {
        assert.expect(1);

        const views = {
            "project.task,false,kanban":
                `<kanban js_class="project_task_kanban" default_group_by="project_id">
                    <templates>
                        <t t-name="kanban-box"/>
                    </templates>
                </kanban>`,
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: "project.task",
            views: [[false, "kanban"]],
        });

        assert.strictEqual(target.querySelector(".o_column_title").innerText, "🔒 Private\n1");
    });

    QUnit.test("Test group label for empty project in pivot", async function (assert) {
        assert.expect(1);

        const views = {
            "project.task,false,pivot":
                `<pivot js_class="project_pivot">
                    <field name="project_id" type="row"/>
                </pivot>`,
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: "project.task",
            views: [[false, "pivot"]],
        });

        assert.strictEqual(
            target.querySelector("tr:nth-of-type(2) .o_pivot_header_cell_closed").innerText,
            "Private",
        );
    });
});
