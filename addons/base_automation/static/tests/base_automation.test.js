import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { animationFrame, expect, test, waitFor } from "@odoo/hoot";
import { Model } from "@web/../tests/_framework/mock_server/mock_model";
import {
    contains,
    defineModels,
    fields,
    getService,
    mountWebClient,
    onRpc,
    webModels,
} from "@web/../tests/web_test_helpers";

test("trigger_selection race condition", async () => {
    defineMailModels();

    webModels.IrModel._records = [
        {
            id: 45,
            display_name: "some_model",
        },
    ];

    webModels.IrModelFields._records = [
        {
            id: 54,
            model_id: 45,
            display_name: "some field",
            ttype: "boolean",
        },
    ];

    let defaultDummy = 0;
    class BaseAuto extends Model {
        selection = fields.Selection({
            selection: [
                ["on_create_or_write", "on_create_or_write"],
                ["on_create", "on_create"],
                ["on_write", "on_write"],
                ["on_change", "on_change"],
            ],
        });
        model_id = fields.Many2one({ relation: "ir.model", default: 45 });
        model_is_mail_thread = fields.Boolean();
        int = fields.Integer({ default: defaultDummy });

        _name = "base_auto";
        _views = {
            form: `<form>
                <field name="selection" widget="base_automation_trigger_selection" />
                <field name="model_id" />
                <field name="int" />
            </form>`,
        };

        onchange() {
            const res = super.onchange(...arguments);
            res.value.int = defaultDummy++;
            return res;
        }
    }
    defineModels([BaseAuto]);
    await mountWebClient();
    const actionService = getService("action");

    let resolversIrModelFiels;
    let resolversOnchange;
    onRpc("onchange", async () => {
        expect.step("onchange");
        await resolversOnchange?.promise;
    });

    onRpc("ir.model.fields", "search_read", async () => {
        expect.step("irmf searchread");
        await resolversIrModelFiels?.promise;
    });

    await actionService.doAction({
        type: "ir.actions.act_window",
        res_model: "base_auto",
        views: [
            [false, "list"],
            [false, "form"],
        ],
        cache: true,
    });

    // Enter form view and leave: this will create an entry in the RPC cache
    // for onchange
    await contains(".o_list_button_add").click();
    await contains(".o_form_button_cancel").click();
    expect.verifySteps(["onchange", "irmf searchread"]);

    // Manage to request the form view to open but with control
    // over RPC cache update and ir.model.fields search read
    // resolve orders.
    resolversIrModelFiels = Promise.withResolvers();
    resolversOnchange = Promise.withResolvers();
    await contains(".o_list_button_add").click();
    await animationFrame();
    resolversOnchange.resolve();
    await Promise.resolve();
    resolversIrModelFiels.resolve();
    expect.verifySteps(["onchange", "irmf searchread"]);

    // Expecting no crash, and correct select values
    await contains(".o_field_base_automation_trigger_selection input").click();
    await waitFor(".o_field_selection_menu");
    expect(".o_field_selection_menu").toHaveText(
        "Custom\non_create_or_write\non_create\non_change"
    );
});
