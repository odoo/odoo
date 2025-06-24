import { beforeEach, expect, test } from "@odoo/hoot";
import { click, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    fields,
    getService,
    mountView,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { WebClient } from "@web/webclient/webclient";
import { ProjectTask } from "./mock_server/mock_models/project_task";
import { defineTodoModels } from "./todo_test_helpers";

defineTodoModels();

beforeEach(() => {
    ProjectTask._views = {
        list: `
            <list js_class="todo_list">
                <field name="name" nolabel="1"/>
                <field name="state" widget="todo_done_checkmark" nolabel="1"/>
            </list>`,
        form: `
            <form string="To-do" class="o_todo_form_view" js_class="todo_form">
                <field name="name"/>
                <field name="priority" invisible="1"/>
                <field name="date_deadline" widget="remaining_days"/>
            </form>`,
        activity: `
            <activity string="MailTestActivity">
                <field name="name" invisible="1"/>
                <templates>
                    <div t-name="activity-box">
                        <field name="name"/>
                    </div>
                </templates>
            </activity>`,
    };

    ProjectTask._fields.activity_state = fields.Selection({
        string: "State",
        selection: [
            ["overdue", "Overdue"],
            ["today", "Today"],
            ["planned", "Planned"],
        ],
    });
});

test("Check that project_task_action_convert_todo_to_task appears in the menu actions if the user does belong to the group_project_user group", async () => {
    onRpc("has_group", () => true);
    await mountView({
        resModel: "project.task",
        resId: 1,
        type: "form",
        actionMenus: {},
    });

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    expect(queryAllTexts(".o-dropdown--menu span")).toInclude("Convert to Task", {
        message:
            "project_task_action_convert_todo_to_task action should appear in the menu actions",
    });
});

test("Check that project_task_action_convert_todo_to_task does not appear in the menu actions if the user does not belong to the group_project_user group", async () => {
    onRpc("has_group", () => false);

    await mountView({
        resModel: "project.task",
        resId: 1,
        type: "form",
        actionMenus: {},
    });

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    expect(queryAllTexts(".o-dropdown--menu span")).not.toInclude("Convert to Task", {
        message:
            "project_task_action_convert_todo_to_task action should appear in the menu actions",
    });
});

test("Check that todo_form view contains the TodoDoneCheckmark and remaining_days widgets", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "To-do",
        res_model: "project.task",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [false, "form"],
        ],
    });

    expect(".o_field_todo_done_checkmark").toHaveCount(3, {
        message: "The todo list view should contain 3 TodoDoneCheckmark widgets",
    });

    await contains(".o_data_cell").click();
    await animationFrame();
    expect(".o_field_remaining_days").toHaveCount(1, {
        message: "The todo form view should have deadline field (o_field_remaining_days)",
    });
});
test.tags("desktop");
test("Check if opening form view from activity view does open with chatter visble", async () => {
    // Basic/Minimum data needed for activity view to be displayed
    onRpc("web_search_read", function ({ model }) {
        return {
            length: 1,
            records: this.env[model].read(1, ["name"]),
        };
    });
    onRpc("get_activity_data", function () {
        return {
            activity_res_ids: [1],
            grouped_activities: {},
            activity_types: this.env["mail.activity.type"].map((type) => {
                const templates = (type.mail_template_ids || []).map((template_id) => {
                    const { id, name } = this.env["mail.template"].browse(template_id)[0];
                    return { id, name };
                });
                return {
                    id: type.id,
                    name: type.display_name,
                    template_ids: templates,
                };
            }),
        };
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "project.task",
        type: "ir.actions.act_window",
        views: [
            [false, "activity"],
            [false, "form"],
        ],
    });
    expect(".o_activity_record").toHaveCount(1);
    click(".o_activity_record");
    // First animationFrame for rendering form view
    await animationFrame();
    // Second animationFrame for re-rendering as chatter is toggled by change in state
    await animationFrame();
    expect("a.todo_toggle_chatter.active").toHaveCount(1);
    expect(browser.localStorage.getItem("isChatterOpened")).toBe(null);
});

test.tags("desktop");
test("check local stored value on click of chatter toggle icon", async () => {
    await mountView({
        resModel: "project.task",
        resId: 1,
        type: "form",
    });

    expect("a.todo_toggle_chatter.active").toHaveCount(0);
    expect(browser.localStorage.getItem("isChatterOpened")).toBe(null);
    click("a.todo_toggle_chatter");
    await animationFrame();
    expect("a.todo_toggle_chatter.active").toHaveCount(1);
    expect(browser.localStorage.getItem("isChatterOpened")).toBe("true");
    click("a.todo_toggle_chatter");
    await animationFrame();
    expect("a.todo_toggle_chatter.active").toHaveCount(0);
    expect(browser.localStorage.getItem("isChatterOpened")).toBe("false");
});
