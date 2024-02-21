/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { addModelNamesToFetch } from "@bus/../tests/helpers/model_definitions_helpers";

import { start } from "@mail/../tests/helpers/test_utils";
import {
    click,
    getFixture,
} from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";

addModelNamesToFetch(["project.project", "project.task"]);

let target;

QUnit.module('Notebook Tasks List tests', {
    beforeEach: async function () {
        const pyEnv = await startServer();
        const projectId = pyEnv['project.project'].create([
            { name: "Project One" },
        ]);
        const userId = pyEnv['res.users'].create([
            { name: "User One", login: 'one', password: 'one' },
        ]);
        pyEnv['project.task'].create([
            { name: 'task one', project_id: projectId, closed_subtask_count: 1, closed_depend_on_count: 1, subtask_count: 4, child_ids: [2, 3, 4, 7], depend_on_ids: [5,6], state: '04_waiting_normal', user_ids: [userId] },
            { name: 'task two', parent_id: 1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], depend_on_ids: [], state: '03_approved' },
            { name: 'task three', parent_id: 1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], depend_on_ids: [], state: '02_changes_requested' },
            { name: 'task four', parent_id: 1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], depend_on_ids: [], state: '1_done' },
            { name: 'task five', closed_subtask_count: 0, subtask_count: 1, child_ids: [6], depend_on_ids: [], state: '03_approved' },
            { name: 'task six', parent_id: 5, closed_subtask_count: 0, subtask_count: 0, child_ids: [], depend_on_ids: [], state: '1_canceled' },
            { name: 'task seven', parent_id: 1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], depend_on_ids: [], state: '01_in_progress', user_ids: [userId] },
        ]);
        this.views = {
            "project.task,false,form":
                `<form>
                    <field name="child_ids" widget="notebook_task_one2many">
                        <tree editable="bottom">
                            <field name="display_in_project" force_save="1"/>
                            <field name="project_id" widget="project"/>
                            <field name="name"/>
                            <field name="state"/>
                        </tree>
                    </field>
                    <field name="depend_on_ids" widget="subtasks_one2many">
                        <tree editable="bottom">
                            <field name="display_in_project" force_save="1"/>
                            <field name="project_id" widget="project"/>
                            <field name="name"/>
                            <field name="state"/>
                        </tree>
                    </field>
                </form>`
        };
        
        target = getFixture();
        setupViewRegistries();
    }
}, function () {
    QUnit.test("Check that the Hide/View closed tasks button works as intended", async function (assert) {
        const views = this.views;
        const { openView } = await start({ serverData: { views } });
        await openView({
            res_model: "project.task",
            views: [[false, "form"]],
            res_id: 1,
        });

        assert.containsN(target, 'div[name="child_ids"] .o_data_row', 4, "The subtasks list should display all subtasks by default, thus we are looking for 4 in total");
        assert.containsN(target, 'div[name="depend_on_ids"] .o_data_row', 2, "The depend on tasks list should display all blocking tasks by default, thus we are looking for 2 in total");

        assert.strictEqual(target.querySelector("div[name='child_ids'] .o_field_x2many_list_row_add a.o_toggle_closed_task_button").innerText, "Hide closed task");
        assert.strictEqual(target.querySelector("div[name='depend_on_ids'] .o_field_x2many_list_row_add a.o_toggle_closed_task_button").innerText, "Hide closed task");

        await click(target.querySelector("div[name='child_ids'] .o_field_x2many_list_row_add a.o_toggle_closed_task_button"));

        assert.strictEqual(target.querySelector("div[name='child_ids'] .o_field_x2many_list_row_add a.o_toggle_closed_task_button").innerText, "Show closed task");
        assert.strictEqual(target.querySelector("div[name='depend_on_ids'] .o_field_x2many_list_row_add a.o_toggle_closed_task_button").innerText, "Hide closed task");

        assert.containsN(target, 'div[name="child_ids"] .o_data_row', 3, "The subtasks list should only display the open subtasks of the task, in this case 3");
        assert.containsN(target, 'div[name="depend_on_ids"] .o_data_row', 2, "The depend on tasks list should still display all blocking tasks, in this case 2");
        
        await click(target.querySelector("div[name='depend_on_ids'] .o_field_x2many_list_row_add a.o_toggle_closed_task_button"));

        assert.strictEqual(target.querySelector("div[name='child_ids'] .o_field_x2many_list_row_add a.o_toggle_closed_task_button").innerText, "Show closed task");
        assert.strictEqual(target.querySelector("div[name='depend_on_ids'] .o_field_x2many_list_row_add a.o_toggle_closed_task_button").innerText, "Show closed task");

        assert.containsN(target, 'div[name="child_ids"] .o_data_row', 3, "The subtasks list should still only display the open subtasks of the task, in this case 3");
        assert.containsN(target, 'div[name="depend_on_ids"] .o_data_row', 1, "The depend on tasks list should only display open tasks, in this case 1");
    });
});
