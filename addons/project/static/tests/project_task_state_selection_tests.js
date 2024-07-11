/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { addModelNamesToFetch } from "@bus/../tests/helpers/model_definitions_helpers";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, getFixture } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";

addModelNamesToFetch([
    'project.project',
    'project.task',
]);

let target;

QUnit.module('Task State Tests', {
    beforeEach: async function () {
        const pyEnv = await startServer();
        const projectId = pyEnv['project.project'].create([
            { name: "Project One" },
        ]);
        const userId = pyEnv['res.users'].create([
            { name: "User One", login: 'one', password: 'one' },
        ]);
        pyEnv['project.task'].create([
            { name: 'task one', project_id: projectId, state: '01_in_progress', user_ids: [userId] },
            { name: 'task two', state: '03_approved' },
            { name: 'task three', state: '04_waiting_normal' },
        ]);
        this.views = {
            "project.task,false,kanban":
                `<kanban js_class="project_task_kanban">
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="state" widget="project_task_state_selection" class="project_task_state_test"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        };
        target = getFixture();
        setupViewRegistries();
    }
}, function () {
    QUnit.test("Check whether task state widget works as intended", async function (assert) {
        const views = this.views;
        const { openView } = await start({ serverData: { views } });
        await openView({
            res_model: "project.task",
            views: [[false, "kanban"]],
        });

        assert.containsNone(target, '.o_field_project_task_state_selection .dropdown-menu', "If the state button has not been pressed yet, no dropdown should be displayed");
        await click(target.querySelector('div[name="state"]:first-child button.dropdown-toggle'));
        assert.containsOnce(target, '.o_field_project_task_state_selection .dropdown-menu', "Once the button has been pressed the dropdown should appear");

        await click(target.querySelector('div[name="state"] .dropdown-menu span.text-danger'));
        const times_button = target.querySelector('div[name="state"]:first-child button.dropdown-toggle i.fa-times-circle');
        assert.ok(times_button, "If the canceled state as been selected, the fa-times-circle icon should be displayed");

        await click(target.querySelector('div[name="state"] i.fa-hourglass-o'));
        const waiting_dropdown_menu = target.querySelector('div[name="state"]:nth-of-type(3) button.dropdown-toggle dropdown-menu');
        assert.notOk(waiting_dropdown_menu , "When trying to click on the waiting icon, no dropdown menu should display");
    });
});
