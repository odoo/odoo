import { describe, expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    getService,
    models,
    mountWithCleanup,
    onRpc,
    switchView,
} from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

class Partner extends models.Model {
    _name = "res.partner";

    many2one_field = fields.Many2one({ relation: "res.partner" });
    many2many_field = fields.Many2many({ relation: "res.partner" });

    _records = [{ id: 1, many2one_field: false, many2many_field: [] }];

    _views = {
        list: `
            <list>
                <field name="many2one_field" widget="many2one_private_placeholder"/>
                <field name="many2many_field" widget="many2many_private_placeholder"/>
            </list>
        `,
        kanban: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="many2one_field" widget="many2one_private_placeholder"/>
                        <field name="many2many_field" widget="many2many_private_placeholder"/>
                    </t>
                </templates>
            </kanban>
        `,
        form: `
            <form>
                <field name="many2one_field" widget="many2one_private_placeholder"/>
                <field name="many2many_field" widget="many2many_private_placeholder"/>
            </form>
        `,
    };
}

defineModels([Partner]);

onRpc("has_group", () => true);

describe.current.tags("desktop");
test("many2x_private_placeholder widget displays the appropriate private label across views", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "res.partner",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [false, "kanban"],
            [false, "form"],
        ],
    });
    const selector1 = `div[name='many2one_field']`;
    const selector2 = `div[name='many2many_field']`;

    expect(".o_control_panel_navigation .o_cp_switch_buttons").toHaveCount(1);
    expect(".o_switch_view").toHaveCount(2);

    expect(".o_list_view .o_content").toHaveCount(1);
    expect(`${selector1} span.text-danger.fst-italic.text-muted`).toHaveText("🔒 Private");
    expect(`${selector2} span.text-danger.fst-italic.text-muted`).toHaveText("🔒 Private");

    await switchView("kanban");
    expect(".o_kanban_view .o_content").toHaveCount(1);
    expect(`${selector1} span.text-danger.fst-italic.text-muted`).toHaveText("🔒 Private");
    expect(`${selector2} span.text-danger.fst-italic.text-muted`).toHaveText("🔒 Private");

    await contains(".o_control_panel_main_buttons .o-kanban-button-new").click();
    expect(".o_form_view .o_content").toHaveCount(1);
    expect(`${selector1} input[placeholder="Private"]`).toHaveCount(1);
    expect(`${selector2} input[placeholder="Private"]`).toHaveCount(1);
});
