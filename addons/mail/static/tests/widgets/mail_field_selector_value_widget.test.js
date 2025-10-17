import {
    click,
    contains,
    openFormView,
    start,
    defineMailModels,
} from "@mail/../tests/mail_test_helpers";
import { test } from "@odoo/hoot";
import { defineModels } from "@web/../tests/web_test_helpers";
import { TestTrackModel, TestTrackOtherModel } from "./field_selector_helper";

defineMailModels();
defineModels([TestTrackModel, TestTrackOtherModel]);

test("mail field selector value changes with the selected field type", async () => {
    await start();
    await openFormView("mail.message.subtype", false, {
        arch: `<form>
            <field name="res_model" invisible="1"/>
            <field name="field_tracked" widget="mail_field_selector" options="{'model': 'res_model', 'only_tracking': True, 'follow_relations': False}" />
            <field name="value_update" widget="mail_field_selector_value" options="{'model': 'res_model', 'value': 'field_tracked', 'accepted_types': ['boolean', 'many2one', 'selection']}"/>
        </form>`,
        context: { default_res_model: "test.track.model" },
    });
    async function clickSelectorAndChooseField(fieldName, options = {}) {
        await click(`div[name='field_tracked'].o_field_widget .o_model_field_selector`);
        await click(".o_model_field_selector_popover_item button", { text: fieldName });
        await contains("div[name='field_tracked'].o_field_widget", { text: fieldName });
        if (options.isNotSupported) {
            await contains("div[name='value_update'].o_field_widget", {
                text: "The field type is not supported for value_update.",
            });
        }
    }

    await clickSelectorAndChooseField("Char", { isNotSupported: true });
    await clickSelectorAndChooseField("Integer", { isNotSupported: true });
    await clickSelectorAndChooseField("Float", { isNotSupported: true });
    await clickSelectorAndChooseField("Many2one");
    await click("div[name='value_update'].o_field_widget input");
    await contains(".o-autocomplete--dropdown-item", { text: "Other 1" });
    await contains(".o-autocomplete--dropdown-item", { text: "Other 2" });
    await contains(".o-autocomplete--dropdown-item", { count: 2 });
    await clickSelectorAndChooseField("Selection");
    await contains("div[name='value_update'] option", { text: "Option 1" });
    await contains("div[name='value_update'] option", { text: "Option 2" });
    await contains("div[name='value_update'] option", { text: "Option 3" });
    await contains("div[name='value_update'] option", { count: 4 }); // including the empty option
    await clickSelectorAndChooseField("Boolean");
    await contains("div[name='value_update'] option", { text: "is set" });
    await contains("div[name='value_update'] option", { text: "is not set" });
    await contains("div[name='value_update'] option", { count: 3 }); // including the empty option
});
