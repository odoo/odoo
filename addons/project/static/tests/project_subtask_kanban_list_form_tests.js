/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { addModelNamesToFetch } from "@bus/../tests/helpers/model_definitions_helpers";

import { start } from "@mail/../tests/helpers/test_utils";

import {
    click,
    getFixture,
    clickOpenedDropdownItem,
    clickDropdown,
} from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";

addModelNamesToFetch(["project.project", "project.task"]);

let target;

QUnit.module('Subtask Kanban List tests', {
    beforeEach: async function () {
        const pyEnv = await startServer();
        const projectId = pyEnv['project.project'].create([
            { name: "Project One" },
        ]);
        const projectId2 = pyEnv['project.project'].create([
            { name: "Project Two" },
        ]);
        const userId = pyEnv['res.users'].create([
            { name: "User One", login: 'one', password: 'one' },
        ]);
        pyEnv['project.task'].create([
            { name: 'task one', project_id: projectId, closed_subtask_count: 1, subtask_count: 4, child_ids: [2, 3, 4, 7], state: '01_in_progress', user_ids: [userId] },
            { name: 'task two', parent_id: 1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: '03_approved' },
            { name: 'task three', parent_id: 1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: '02_changes_requested' },
            { name: 'task four', parent_id: 1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: '1_done' },
            { name: 'task five', closed_subtask_count: 0, subtask_count: 1, child_ids: [6], state: '03_approved' },
            { name: 'task six', parent_id: 5, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: '1_canceled' },
            { name: 'task seven', parent_id: 1, closed_subtask_count: 0, subtask_count: 0, child_ids: [], state: '01_in_progress', user_ids: [userId] },
        ]);
        this.task = pyEnv['project.task'].create([
            { name: "task's Project Two", project_id: projectId2, child_ids: [] }
        ]);
        this.views = {
            "project.task,false,kanban":
                `<kanban js_class="project_task_kanban">
                    <field name="subtask_count"/>
                    <field name="closed_subtask_count"/>
                    <field name="project_id"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="name"/>
                                <field name="user_ids" invisible="1" widget="many2many_avatar_user"/>
                                <field name="state" invisible="1" widget="project_task_state_selection"/>
                                <a t-if="record.closed_subtask_count.raw_value">
                                    <span title="See Subtasks" class="subtask_list_button fa fa-check-square-o me-1"/>
                                    <t t-out="record.closed_subtask_count.value"/>/<t t-out="record.subtask_count.value"/>
                                </a>
                                <div class="kanban_bottom_subtasks_section"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            "project.task,false,form":
                `<form>
                    <field name="child_ids" widget="subtasks_one2many">
                        <tree editable="bottom">
                            <field name="display_in_project" force_save="1"/>
                            <field name="project_id" widget="project"/>
                        </tree>
                    </field>
                </form>`
        };
        target = getFixture();
        setupViewRegistries();
    }
}, function () {
    QUnit.test("Check whether subtask list functionality works as intended", async function (assert) {
        assert.expect(8);

        const views = this.views;
        const { openView } = await start({ serverData: { views } });
        await openView({
            res_model: "project.task",
            views: [[false, "kanban"]],
        });

        assert.containsOnce(target, '.subtask_list_button', "Only kanban boxes of parent tasks having open subtasks should have the drawdown button, in this case this is 1");
        assert.containsNone(target, '.subtask_list', "If the drawdown button is not clicked, the subtasks list should be hidden");

        await click(target, '.subtask_list_button');

        assert.containsOnce(target, '.subtask_list', "Clicking on the button should make the subtask list render, in this case we are expectig 1 list");
        assert.containsN(target, '.subtask_list_row', 3, "The list rendered should show the open subtasks of the task, in this case 3");
        assert.containsN(target, '.subtask_state_widget_col', 3, "Each of the list's rows should have 1 state widget, thus we are looking for 3 in total");
        assert.containsN(target, '.subtask_user_widget_col', 3, "Each of the list's rows should have 1 user widgets, thus we are looking for 3 in total");
        assert.containsN(target, '.subtask_name_col', 3, "Each of the list's rows should display the subtask's name, thus we are looking for 3 in total");

        await click(target, '.subtask_list_button');

        assert.containsNone(target, '.subtask_list', "If the drawdown button is clicked again, the subtasks list should be hidden again");
    });

    QUnit.test("Update closed subtask count in the kanban card when the state of a subtask is set to Done.", async function (assert) {
        let checkSteps = false;
        const { openView } = await start({
            serverData: { views: this.views },
            mockRPC(route, { model, method }) {
                if (checkSteps) {
                    assert.step(`${model}/${method}`);
                }
            },
        });
        await openView({
            res_model: "project.task",
            views: [[false, "kanban"]],
        });

        assert.strictEqual(target.querySelector(".subtask_list_button").parentElement.textContent, "1/4");
        checkSteps = true;
        await click(target, '.subtask_list_button');
        const subtaskEl = target.querySelector(".subtask_list");
        assert.containsOnce(subtaskEl, ".o_field_widget.o_field_project_task_state_selection.subtask_state_widget_col .o_status:not(.o_status_green,.o_status_bubble)", "The state of the subtask should be in progress");
        await click(subtaskEl, ".o_field_widget.o_field_project_task_state_selection.subtask_state_widget_col .o_status:not(.o_status_green,.o_status_bubble)");
        assert.containsNone(subtaskEl, ".o_field_widget.o_field_project_task_state_selection.subtask_state_widget_col .o_status:not(.o_status_green,.o_status_bubble)", "The state of the subtask should no longer be in progress");
        assert.containsOnce(subtaskEl, ".o_field_widget.o_field_project_task_state_selection.subtask_state_widget_col .fa-check-circle.text-success", "The state of the subtask should be Done");
        assert.verifySteps([
            "project.task/search_read",
            "project.task/web_save",
            "project.task/search_read",
            "project.task/web_read", // read the parent task to recompute the subtask count
        ]);
    });

    QUnit.test("Check that the sub task of another project can be added", async function (assert) {
        assert.expect(1);
        const { openView } = await start({
            serverData: { views: this.views },
        });
        await openView({
            res_model: "project.task",
            views: [[false, "form"]],
            res_id: this.task,
        });
        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        await clickDropdown(target, 'project_id');
        await clickOpenedDropdownItem(target, 'project_id', 'Project One');
        await click(target, ".o_form_button_save");
        assert.equal(target.querySelector('.o_field_project').textContent.trim(), 'Project One')
    });

});
