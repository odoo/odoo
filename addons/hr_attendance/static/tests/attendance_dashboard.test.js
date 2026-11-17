import { expect, test } from "@odoo/hoot";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class HrAttendance extends models.Model {
    _name = "hr.attendance";

    name = fields.Char();
    employee = fields.Char();
    state = fields.Selection({
        selection: [
            ["draft", "To Review"],
            ["validated", "Reviewed"],
        ],
    });

    _records = [
        { id: 1, name: "Monday", employee: "Marc", state: "draft" },
        { id: 2, name: "Tuesday", employee: "Marc", state: "draft" },
        { id: 3, name: "Monday", employee: "Anita", state: "draft" },
    ];

    _views = {
        search: `
            <search>
                <filter name="state_draft" string="To Review" domain="[('state', '=', 'draft')]"/>
                <filter name="state_validated" string="Reviewed" domain="[('state', '=', 'validated')]"/>
            </search>`,
        list: `
            <list js_class="attendance_list_view">
                <field name="name"/>
                <field name="state"/>
                <button name="action_validate" type="object" string="Approve"/>
            </list>`,
    };
}

defineModels([HrAttendance]);
defineMailModels();

onRpc("hr.attendance", "get_attendance_dashboard_data", function ({ args }) {
    expect.step(`counters of ${JSON.stringify(args[0])}`);
    const domain = [...args[0], ["state", "=", "draft"]];
    return { to_review: this.env["hr.attendance"].search_count(domain) };
});
onRpc("hr.attendance", "action_validate", function ({ args }) {
    this.env["hr.attendance"].write(args[0], { state: "validated" });
    return true;
});

test("the counters are those of the action's records, whatever the search", async () => {
    await mountView({
        type: "list",
        resModel: "hr.attendance",
        domain: [["employee", "=", "Marc"]],
    });
    expect(".o_attendance_kpi[name='to_review'] .o_attendance_kpi_value").toHaveText("2");
    expect.verifySteps([`counters of [["employee","=","Marc"]]`]);

    await contains(".o_attendance_kpi[name='to_review']").click();
    expect(".o_attendance_kpi[name='to_review']").toHaveAttribute("aria-pressed", "true");
    expect(".o_data_row").toHaveCount(2);
    expect(".o_attendance_kpi[name='to_review'] .o_attendance_kpi_value").toHaveText("2");
    // reloaded with the list, without the search
    expect.verifySteps([`counters of [["employee","=","Marc"]]`]);
});

test("the counters follow the reviews made from the list", async () => {
    await mountView({
        type: "list",
        resModel: "hr.attendance",
        domain: [["employee", "=", "Marc"]],
    });
    expect(".o_attendance_kpi[name='to_review'] .o_attendance_kpi_value").toHaveText("2");
    expect.verifySteps([`counters of [["employee","=","Marc"]]`]);

    await contains(".o_data_row:first-child button[name='action_validate']").click();
    expect(".o_data_row:first-child .o_data_cell[name='state']").toHaveText("Reviewed");
    expect(".o_attendance_kpi[name='to_review'] .o_attendance_kpi_value").toHaveText("1");
    expect.verifySteps([`counters of [["employee","=","Marc"]]`]);
});

test("the counters are not shown on My Attendances", async () => {
    await mountView({
        type: "list",
        resModel: "hr.attendance",
        context: { my_attendances: true },
    });
    expect(".o_attendance_kpi").toHaveCount(0);
    expect.verifySteps([]);
});
