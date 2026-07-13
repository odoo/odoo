/** @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { registry } from "@web/core/registry";
import { makeFakeUserService } from "@web/../tests/helpers/mock_services";
import { click, editInput, getFixture, nextTick } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";

let target;
let serverData;
let mockRPC;

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
        pyEnv.mockServer.models["project.task.type.delete.wizard"] = {
            fields: {
                tasks_count: { string: "Number of Tasks", type: "integer" },
                stages_active: { string: "Stages Active", type: "boolean" },
                project_ids: { string: "Projects", type: "many2many", relation: "project.project" },
                stage_ids: { string: "Stages To Delete", type: "many2many", relation: "project.task.type" },
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
                "project.task.type.delete.wizard,false,form": `
                    <form string="Delete Stage">
                        <footer>
                            <button string="Delete" type="object" name="action_unlink" class="btn btn-primary"/>
                            <button string="Discard" special="cancel"/>
                        </footer>
                    </form>
                `,
            },
        };
        mockRPC = async (route, args) => {
            if (args.method === "unlink_wizard") {
                return {
                    type: "ir.actions.act_window",
                    name: "Delete Stage",
                    res_model: "project.task.type.delete.wizard",
                    view_mode: "form",
                    views: [[false, "form"]],
                    target: "new",
                    res_id: 1,
                };
            }
            if (args.method === "action_unlink") {
                return {
                    type: "ir.actions.act_window_close",
                    infos: {
                        success: true,
                    },
                }
            }
        };
        target = getFixture();
        setupViewRegistries();
        serviceRegistry.add(
            "user",
            makeFakeUserService((group) => group === "project.group_project_manager"),
            { force: true }
        );
    });
    QUnit.test("delete a column in grouped on m2o", async function (assert) {
        const { openView } = await start({ serverData });

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
    QUnit.test("delete just created stage", async function (assert) {
        const { openView } = await start({ serverData, mockRPC });

        await openView({
            res_model: "project.task",
            views: [[false, "kanban"]],
            context: {
                active_model: "project.project",
                default_project_id: 1,
            },
        });

        await editInput(target.querySelector(".o_column_quick_create input"), null, "Stage 1");
        await click(target, ".o_kanban_add");

        await click(target, ".o_kanban_group:first-child .o_kanban_config.dropdown .dropdown-toggle");
        await click(target, ".dropdown-item.o_column_delete");
        await click(target, "button[special=cancel]");
        assert.containsOnce(target, ".o_column_title", "The stage should not have been deleted.");

        await click(target, ".o_kanban_group:first-child .o_kanban_config.dropdown .dropdown-toggle");
        await click(target, ".dropdown-item.o_column_delete");
        await click(target, "button[name=action_unlink]");
        assert.containsNone(target, ".o_column_title", "The stage should have been deleted.");
    });
    QUnit.test("delete existing stage", async function (assert) {
        const originalMockRPC = mockRPC;
        mockRPC = async (route, args) => {
            if (args.method === "web_read_group") {
                return {
                    groups: [{ stage_id: [1, "Stage 1"] }],
                    length: 1,
                };
            }
            return originalMockRPC(route, args);
        };
        const { openView } = await start({ serverData, mockRPC });

        await openView({
            res_model: "project.task",
            views: [[false, "kanban"]],
            context: {
                active_model: "project.project",
                default_project_id: 1,
            },
        });

        await click(target, ".o_kanban_group:first-child .o_kanban_config.dropdown .dropdown-toggle");
        await click(target, ".dropdown-item.o_column_delete");
        await click(target, "button[special=cancel]");
        assert.containsOnce(target, ".o_column_title", "The stage should not have been deleted.");

        await click(target, ".o_kanban_group:first-child .o_kanban_config.dropdown .dropdown-toggle");
        await click(target, ".dropdown-item.o_column_delete");
        await click(target, "button[name=action_unlink]");
        assert.containsNone(target, ".o_column_title", "The stage should have been deleted.");
    });
});
