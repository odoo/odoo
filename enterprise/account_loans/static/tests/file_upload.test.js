import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    contains,
    defineModels,
    fields,
    getMockEnv,
    mockService,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { expect, test, tick } from "@odoo/hoot";

class Partner extends models.Model {
    name = fields.Char();

    _records = [
        { id: 1, name: "Albert" },
        { id: 2, name: "Lucie" },
    ];
}

defineMailModels();
defineModels([Partner]);

test("new_loan widget compute action is called", async () => {
    onRpc("account.loan", "action_open_compute_wizard", ({ args }) => {
        return {
            res_id: 2,
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        };
    });

    onRpc("partner", "web_save", async () => {
        await tick();
        expect.step("web_save");
    });

    mockService("action", {
        doAction: () => expect.step("doAction"),
    });

    await mountView({
        resModel: "partner",
        type: "form",
        resId: 1,
        arch: `
            <form>
                <header>
                    <button name="action_1" string="An action"/>
                    <widget name="new_loan"/>
                </header>
                <group>
                    <group>
                        <field name="name"/>
                    </group>
                </group>
            </form>
        `,
    });

    await contains(".o_field_widget[name=name] input").edit("a new name");

    if (getMockEnv().isSmall) {
        await contains(".o_cp_action_menus button > .fa-cog").click();
        await contains(".o-dropdown--menu button:contains('Compute')").click();
    } else {
        await contains(".o_form_statusbar button:contains('Compute')").click();
    }

    await expect.waitForSteps(["web_save", "doAction"]);
});
