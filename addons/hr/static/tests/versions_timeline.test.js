import { expect, test } from "@odoo/hoot";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    defineActions,
    defineModels,
    fields,
    getService,
    models,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

class HrVersion extends models.Model {
    _name = "hr.version";
    _rec_name = "name";

    name = fields.Char();
    employee_id = fields.Many2one({ relation: "hr.employee" });

    _records = [
        { id: 10, name: "Jan 01, 2024", employee_id: 1 },
        { id: 11, name: "Jan 01, 2025", employee_id: 1 },
    ];
}

class HrEmployee extends models.Model {
    _name = "hr.employee";

    name = fields.Char();
    version_id = fields.Many2one({ relation: "hr.version" });
    version_revision = fields.Integer();

    _records = [{ id: 1, name: "Employee", version_id: 11, version_revision: 0 }];

    _views = {
        form: /* xml */ `
            <form>
                <header>
                    <field name="version_id" widget="versions_timeline"
                        context="{'version_revision': version_revision}"/>
                    <field name="version_revision" invisible="1"/>
                </header>
            </form>
        `,
    };
}

defineModels([HrEmployee, HrVersion]);
defineMailModels();

test("versions_timeline widget fetches display_name on a full-page form", async () => {
    onRpc("hr.version", "search_read", ({ kwargs }) => expect.step(kwargs.fields.toString()));
    defineActions([
        { id: 1, name: "Employee", res_model: "hr.employee", res_id: 1, views: [[false, "form"]] },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    expect.verifySteps(["display_name"]);
    expect(".o_arrow_button_current").toHaveText("Jan 01, 2025");
});

test("versions_timeline widget still fetches display_name when the form is opened in a dialog", async () => {
    onRpc("hr.version", "search_read", ({ kwargs }) => expect.step(kwargs.fields.toString()));
    defineActions([
        {
            id: 1,
            name: "Employee",
            res_model: "hr.employee",
            res_id: 1,
            views: [[false, "form"]],
            target: "new",
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    expect(".o_dialog .o_form_view .o_control_panel").toHaveCount(0);
    expect.verifySteps(["display_name"]);
    expect(".o_dialog .o_arrow_button_current").toHaveText("Jan 01, 2025");
});
