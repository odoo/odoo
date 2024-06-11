/* @odoo-module */

import { registry } from "@web/core/registry";
import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { addModelNamesToFetch } from "@bus/../tests/helpers/model_definitions_helpers";
import { makeFakeUserService } from "@web/../tests/helpers/mock_services";

import { start } from "@mail/../tests/helpers/test_utils";

import {  getFixture, click } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";

const serviceRegistry = registry.category("services");

addModelNamesToFetch(["project.project", "project.task", "project.task.type"]);

let target;

QUnit.module('Project', {
    beforeEach: async function () {
        const pyEnv = await startServer();
        const projectId = pyEnv['project.project'].create([
            { name: "Project One" },
        ]);
        const stageId = pyEnv['project.task.type'].create([
            { name: "New" },
        ]);
        pyEnv['project.task'].create([
            { name: 'task one', project_id: projectId, stage_id: stageId },
        ]);
        this.views = {
            "project.task,false,kanban":
                `<kanban js_class="project_task_kanban">
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        };
        target = getFixture();
        setupViewRegistries();
    }
}, function () {
    QUnit.test("quick create button is visible when the user has access rights.", async function (assert) {
        serviceRegistry.add(
            "user",
            makeFakeUserService((group) => group === "project.group_project_manager"),
            { force: true },
        );
        const { views } = this;
        const { openView } = await start({ serverData: { views } });
        await openView({
            res_model: "project.task",
            views: [[false, "kanban"]],
            context: {
                active_model: "project.project",
                default_project_id: 1,
                group_by: ["stage_id"],
            },
        });

        assert.containsOnce(target, ".o_column_quick_create", "The quick create button should be visible.");
        await click(target, ".o_kanban_add_column");
    });

    QUnit.test("quick create button is not visible when the user not have access rights.", async function (assert) {
        const { views } = this;
        const { openView } = await start({ serverData: { views } });
        await openView({
            res_model: "project.task",
            views: [[false, "kanban"]],
            context: {
                active_model: "project.project",
                default_project_id: 1,
                group_by: ["stage_id"],
            },
        });

        assert.containsNone(target, ".o_column_quick_create", "The quick create button should be hidden.");
    });
});
