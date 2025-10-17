import {
    click,
    contains,
    defineMailModels,
    openFormView,
    start,
} from "@mail/../tests/mail_test_helpers";
import { test } from "@odoo/hoot";
import { defineModels } from "@web/../tests/web_test_helpers";
import { TestTrackModel, TestTrackOtherModel } from "./field_selector_helper";

defineMailModels();
defineModels([TestTrackModel, TestTrackOtherModel]);

test("mail field selector takes the given model and opens a popup with the tracking fields", async () => {
    await start();
    await openFormView("mail.message.subtype", false, {
        arch: `<form>
            <field name="res_model" invisible="1"/>
            <field name="field_tracked" widget="mail_field_selector" options="{'model': 'res_model', 'only_tracking': True, 'follow_relations': False}"/>
        </form>`,
        context: { default_res_model: "test.track.model" },
    });
    await click("div[name='field_tracked'].o_field_widget .o_model_field_selector");
    await contains(".o_model_field_selector_popover_item", { text: "Boolean" });
    await contains(".o_model_field_selector_popover_item", { count: 6 });
    await click(".o_model_field_selector_popover_item button", { text: "Boolean" });
    await contains("div[name='field_tracked'].o_field_widget", { text: "Boolean" });
});
