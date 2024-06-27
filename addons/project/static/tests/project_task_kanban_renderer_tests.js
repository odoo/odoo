/** @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";

let target;
let serverData;


QUnit.module("project", (hooks) => {
    hooks.beforeEach(async () => {
        const pyEnv = await startServer();
        pyEnv.mockServer.models["project.project"] = {
            fields: {
                id: { string: "ID", type: "integer" },
                display_name: { string: "Name", type: "char" },
            },
            records: [],
        };
        pyEnv.mockServer.models["project.task"] = {
            fields: {
                id: { string: "Id", type: "integer" },
                name: { string: "Name", type: "char" },
                sla_deadline: {
                    string: "SLA Deadline",
                    type: "date",
                    store: true,
                    sortable: true,
                    groupable: true,
                },
                project_id: { string: "Project", type: "many2one", relation: "project.project" },
                stage_id: { string: "Stage", type: "many2one", relation: "project.task.type" },
            },
            records: [],
        };
        serverData = {
            views: {
                "project.task,false,kanban": `
                    <kanban default_group_by="stage_id" js_class="project_task_kanban">
                        <field name="name"/>
                        <templates>
                            <t t-name="kanban-box">
                                <div>
                                    <field name="name"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>
                `,
            },
        };
        target = getFixture();
        setupViewRegistries();
    });
    QUnit.test("delete a column in grouped on m2o", async function (assert) {
<<<<<<< HEAD
        const groups = [
            {
                stage_id: [1, "New"],
                __domain: [],
            },
        ];
        const { openView } = await start({
            serverData,
            async mockRPC({ model, method }) {
                if (method === "web_read_group") {
                    return {
                        groups,
                        length: groups.length,
                    };
                }
                if (model === "project.task.type" && method === "unlink_wizard") {
                    assert.step(`${model}/${method}`);
                    return {
                        name: "Delete Stage",
                        type: "ir.actions.act_window",
                        target: "new",
                        view_mode: "form",
                        res_model: "project.task.type.delete.wizard",
                        views: [[false, "form"]],
                    };
                }
            },
        });
||||||| parent of bc8e3afe3346 (temp)
        serviceRegistry.add(
            "user",
            makeFakeUserService((group) => group === "project.group_project_manager"),
            { force: true }
        );
        const groups = [
            {
                stage_id: [1, "New"],
                __domain: [],
            },
        ];
        const { openView } = await start({
            serverData,
            async mockRPC({ model, method }) {
                if (method === "web_read_group") {
                    return {
                        groups,
                        length: groups.length,
                    };
                }
                if (model === "project.task.type" && method === "unlink_wizard") {
                    assert.step(`${model}/${method}`);
                    return {
                        name: "Delete Stage",
                        type: "ir.actions.act_window",
                        target: "new",
                        view_mode: "form",
                        res_model: "project.task.type.delete.wizard",
                        views: [[false, "form"]],
                    };
                }
            },
        });
=======
        serviceRegistry.add(
            "user",
            makeFakeUserService((group) => group === "project.group_project_manager"),
            { force: true }
        );
        const { openView } = await start({ serverData });

>>>>>>> bc8e3afe3346 (temp)
        await openView({
            res_model: "project.task",
            views: [[false, "kanban"]],
            context: {
                'active_model': "project.task.type.delete.wizard",
                'default_project_id': 1,
            },
        });

        assert.containsN(target, ".o_kanban_header", 1, "should have 1 column");
        await nextTick();
        assert.containsOnce(target, ".o_column_quick_create");

        assert.containsN(
            target,
            ".o_kanban_example_background_container",
            1,
            "ghost column visible"
        );
    });
});
