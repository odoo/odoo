/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { addModelNamesToFetch } from "@bus/../tests/helpers/model_definitions_helpers";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, getFixture, getNodesTextContent } from "@web/../tests/helpers/utils";
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
        this.tasks = pyEnv['project.task'].create([
            { name: 'task one', project_id: projectId, state: '01_in_progress', user_ids: [userId] },
            { name: 'task two', state: '03_approved' },
            { name: 'task three', state: '04_waiting_normal' },
        ]);
        this.views = {
            "project.task,false,kanban":
                `<kanban js_class="project_task_kanban">
                    <templates>
                        <t t-name="card">
                            <field name="state" widget="project_task_state_selection" class="project_task_state_test"/>
                        </t>
                    </templates>
                </kanban>`,
            "project.task,false,form": `
                <form js_class="project_task_form">
                    <field name="project_id"/>
                    <field name="name"/>
                    <field name="state" widget="project_task_state_selection"/>
                </form>
            `,
        };
        target = getFixture();
        setupViewRegistries();
    }
}, function () {
    QUnit.test("Test task state widget in kanban", async function (assert) {
        const views = this.views;
        const { openView } = await start({ serverData: { views } });
        await openView({
            res_model: "project.task",
            views: [[false, "kanban"]],
        });

        assert.containsNone(target, '.o-dropdown--menu', "If the state button has not been pressed yet, no dropdown should be displayed");
        await click(target.querySelector('div[name="state"]:first-child button.dropdown-toggle'));
        assert.containsOnce(target, '.o-dropdown--menu', "Once the button has been pressed the dropdown should appear");

        await click(target.querySelector('.o-dropdown--menu span.text-danger'));
        const times_button = target.querySelector('div[name="state"]:first-child button.dropdown-toggle i.fa-times-circle');
        assert.ok(times_button, "If the canceled state as been selected, the fa-times-circle icon should be displayed");

        await click(target.querySelector('div[name="state"] i.fa-hourglass-o'));
        const waiting_dropdown_menu = target.querySelector('.o-dropdown--menu');
        assert.notOk(waiting_dropdown_menu , "When trying to click on the waiting icon, no dropdown menu should display");
    });

    QUnit.test("Test task state widget in form", async function (assert) {
        const clickStateButton = () => click(target.querySelector("button.o_state_button"));
        const getDropdownItems = () =>
            target.querySelectorAll(".state_selection_field_menu .dropdown-item");
        const { views, tasks: [task1, , task3] } = this;
        const { openView } = await start({ serverData: { views } });

        await openView({
            res_model: "project.task",
            res_id: task1,
            views: [[false, "form"]],
        }).then(clickStateButton);
        assert.deepEqual(getNodesTextContent(getDropdownItems()), [
            "In Progress",
            "Changes Requested",
            "Approved",
            "Cancelled",
            "Done",
        ]);

        await openView({
            res_model: "project.task",
            res_id: task3,
            views: [[false, "form"]],
        }).then(clickStateButton);
        assert.deepEqual(getNodesTextContent(getDropdownItems()), ["Cancelled", "Done"]);
    });
});
