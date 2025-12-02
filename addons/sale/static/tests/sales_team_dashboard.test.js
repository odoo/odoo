import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class CRMTeam extends models.Model {
    _name = "crm.team";

    foo = fields.Char();
    invoiced = fields.Integer();
    invoiced_target = fields.Integer();

    _records = [{ id: 1, foo: "yop", invoiced: 0, invoiced_target: 0 }];
}

defineModels([CRMTeam]);
defineMailModels();

test("edit progressbar target", async () => {
    mockService("action", {
        doAction(action) {
            expect(action).toEqual(
                {
                    res_model: "crm.team",
                    target: "current",
                    type: "ir.actions.act_window",
                    method: "get_formview_action",
                },
                { message: "should trigger do_action with the correct args" }
            );
            expect.step("doAction");
            return true;
        },
    });

    onRpc("crm.team", "get_formview_action", ({ method, model }) => ({
        method,
        res_model: model,
        target: "current",
        type: "ir.actions.act_window",
    }));

    await mountView({
        type: "kanban",
        resModel: "crm.team",
        arch: /* xml */ `
            <kanban>
                <field name="invoiced_target"/>
                <templates>
                    <div t-name="card">
                        <field name="invoiced" widget="sales_team_progressbar" options="{'current_value': 'invoiced', 'max_value': 'invoiced_target', 'editable': true, 'edit_max_value': true}"/>
                    </div>
                </templates>
            </kanban>`,
        resId: 1,
    });

    expect(
        ".o_field_sales_team_progressbar:contains(Click to define an invoicing target)"
    ).toHaveCount(1);
    expect(".o_progressbar input").toHaveCount(0);

    await contains(".sale_progressbar_form_link").click(); // should trigger a do_action
    expect.verifySteps(["doAction"]);
});
