import { test, expect, beforeEach } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import { mountView, contains, onRpc } from "@web/../tests/web_test_helpers";

import { defineTodoModels } from "./todo_test_helpers";
import { ProjectTask } from "./mock_server/mock_models/project_task";

defineTodoModels();

beforeEach(() => {
    ProjectTask._views = {
        form: `
            <form string="To-do" class="o_todo_form_view" js_class="todo_form">
                <field name="priority" invisible="1"/>
                <field name="state" invisible="1"/>
                <field name="name"/>
            </form>`,
        "form,2": `
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
    };
});

test("Check that todo_conversion_form view focuses on the focus on the first element", async () => {
    onRpc("/web/action/load", () => {
        return {
            type: "ir.actions.act_window",
            name: "Convert to Task",
            res_model: "project.task",
            view_mode: "form",
            target: "new",
            views: [[2, "form"]],
        };
    });

    await mountView({
        resModel: "project.task",
        resId: 1,
        type: "form",
        actionMenus: {},
    });

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await contains(".o-dropdown-item:contains('Convert to Task')").click();
    await animationFrame();
    expect(queryAll("div.o_todo_conversion_form_view input")[0]).toBeFocused({
        message: "The first element should be focused",
    });
});
