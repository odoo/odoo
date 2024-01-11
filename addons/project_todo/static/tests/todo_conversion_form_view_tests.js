/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { addModelNamesToFetch } from "@bus/../tests/helpers/model_definitions_helpers";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, getFixture } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";

import { patchUserWithCleanup } from "@web/../tests/helpers/mock_services";

addModelNamesToFetch(["project.task", "project.tags", "project.project"]);

let serverData;
let target;

QUnit.module("todoConversionFormView Tests", (hooks) => {
    hooks.beforeEach(async () => {
        const pyEnv = await startServer();
        pyEnv["project.task"].create([{}]); // To simulate a todo element
        serverData = {
            views: {
                "project.task,false,list": `
                    <tree>
                        <field name="id"/>
                    </tree>`,
                "project.task,1,form": `
                    <form js_class="todo_form">
                        <field name="id"/>
                    </form>`,
                "project.task,2,form": `
                    <form string="Convert to Task" js_class="todo_conversion_form">
                    <sheet>
                        <group>
                            <field name="company_id" invisible="1"/>
                            <field name="project_id"
                                required="1"
                                placeholder="Select an existing project"
                                default_focus="1"/>
                            <field name="user_ids"
                                class="o_task_user_field"
                                options="{'no_open': True, 'no_quick_create': True}"
                                widget="many2many_avatar_user"
                                domain="[('share', '=', False), ('active', '=', True)]"/>
                            <field name="tag_ids" widget="many2many_tags"
                                options="{'color_field': 'color', 'no_create_edit': True}"
                                context="{'project_id': project_id}"
                                placeholder="Choose tags from the selected project"/>
                        </group>
                    </sheet>
                    <footer>
                        <button name="action_convert_to_task" string="Convert to Task" type="object" class="btn-primary"/>
                        <button string="Discard" special="cancel"/>
                    </footer>
                </form>`,
            },
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.test("Check that todo_conversion_form view focuses on the focus on the first element", async function (assert) {
        assert.expect(1);
        const { openView } = await start({
            serverData,
            async mockRPC(route) {
                if (route === "/web/action/load") {
                    return {
                        type: "ir.actions.act_window",
                        name: "Convert to Task",
                        res_model: "project.task",
                        view_mode: "form",
                        target: "new",
                        views: [[2, "form"]],
                    };
                }
            },
        });
        await openView({
            res_model: "project.task",
            views: [
                [false, "list"],
                [1, "form"],
            ],
        });
        patchUserWithCleanup({ hasGroup: async (group) => group === "project.group_project_user" }); // For the user to have access to project_task_action_convert_todo_to_task
        await click(target.querySelector(".o_data_cell"));
        await click(target.querySelector(".o_cp_action_menus button"));
        const menuActions = target.querySelectorAll(".o-dropdown--menu span");
        for (const actionEl of menuActions) {
            if (actionEl.innerText === "Convert to Task") {
                await click(actionEl);
                break;
            }
        }
        assert.strictEqual(
            document.activeElement,
            target.querySelector("div.o_todo_conversion_form_view input"),
            "The first element should be focused"
        );
    });
});
