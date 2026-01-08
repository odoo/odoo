/** @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { start } from "@mail/../tests/helpers/test_utils";
import { click, getFixture, getNodesTextContent } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";

let target;

QUnit.module(
    "Project Task Form View",
    {
        beforeEach: async function () {
            const pyEnv = await startServer();
            const projectId = pyEnv["project.project"].create([{ name: "Project One" }]);
            const stageId = pyEnv["project.task.type"].create([{ name: "New" }]);
            [this.task1, this.task2] = pyEnv["project.task"].create([
                {
                    name: "task one",
                    project_id: projectId,
                    stage_id: stageId,
                    state: "03_approved",
                },
                {
                    name: "task two",
                    project_id: projectId,
                    stage_id: stageId,
                    state: "04_waiting_normal",
                },
            ]);
            this.views = {
                "project.task,false,form": `
                    <form js_class="project_task_form">
                        <field name="project_id"/>
                        <field name="stage_id"/>
                        <field name="name"/>
                        <field name="state" widget="project_task_state_selection"/>
                    </form>
                `,
            };
            target = getFixture();
            setupViewRegistries();
        },
    },
    function () {
        QUnit.test("project task form view", async function (assert) {
            const clickStateButton = () => click(target.querySelector("button.o_state_button"));
            const { task1, task2, views } = this;
            const { openView } = await start({ serverData: { views } });

            await openView({
                res_model: "project.task",
                res_id: task1,
                views: [[false, "form"]],
            }).then(clickStateButton);
            assert.deepEqual(
                getNodesTextContent(target.querySelectorAll("div[name='state'] .dropdown-item")),
                ["In Progress", "Changes Requested", "Approved", "Canceled", "Done"]
            );

            await openView({
                res_model: "project.task",
                res_id: task2,
                views: [[false, "form"]],
            }).then(clickStateButton);
            assert.deepEqual(
                getNodesTextContent(target.querySelectorAll("div[name='state'] .dropdown-item")),
                ["Canceled", "Done"]
            );
        });
    }
);
