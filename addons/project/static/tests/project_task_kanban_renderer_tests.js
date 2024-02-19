/** @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { registry } from "@web/core/registry";
import { makeFakeUserService } from "@web/../tests/helpers/mock_services";
import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";

let target;
let serverData;

const serviceRegistry = registry.category("services");

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
                    <kanban default_group_by="stage_id">
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
                "project.task.type.delete.wizard,false,form": `
                    <form>
                        <field name="tasks_count" invisible="1" />
                        <field name="stages_active" invisible="1" />
                        <div attrs="{'invisible': [('tasks_count', '>', 0)]}">
                            <p>Are you sure you want to delete these stages?</p>
                        </div>
                        <div attrs="{'invisible': ['|', ('stages_active', '=', False), ('tasks_count', '=', 0)]}">
                            <p>You cannot delete stages containing tasks. You can either archive them or first delete all of their tasks.</p>
                        </div>
                        <div attrs="{'invisible': ['|', ('stages_active', '=', True), ('tasks_count', '=', 0)]}">
                            <p>You cannot delete stages containing tasks. You should first delete all of their tasks.</p>
                        </div>
                        <footer>
                            <button string="Archive Stages" type="object" name="action_archive" class="btn btn-primary" attrs="{'invisible': ['|', ('stages_active', '=', False), ('tasks_count', '=', 0)]}" data-hotkey="q"/>
                            <button string="Delete" type="object" name="action_unlink" class="btn btn-primary" attrs="{'invisible': [('tasks_count', '>', 0)]}" data-hotkey="w"/>
                            <button string="Discard" special="cancel" data-hotkey="z" />
                        </footer>
                    </form>
                `,
            },
        };
        target = getFixture();
        setupViewRegistries();
    });
    QUnit.test("delete a column in grouped on m2o", async function (assert) {
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
        await openView({
            res_model: "project.task",
            views: [[false, "kanban"]],
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
