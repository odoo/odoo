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

test("Dynamic domain takes context into account", async () => {
    await start();
    await openFormView("mail.message.subtype", false, {
        arch: `<form>
            <field name="res_model" invisible="1"/>
            <field name="domain" widget="dynamic_domain" context="{'default_dynamic_domain_model': res_model}"/>
        </form>`,
        context: { default_res_model: "test.track.model" },
    });
    await click("a", { text: "New Rule" });
    await click(".o_model_field_selector_value");
    await contains(".o_model_field_selector_popover_item", { count: 10 });
    await click("button", { text: "Selection" });
    await contains("option", { text: "Option 1" });
    await contains("option", { text: "Option 2" });
    await contains("option", { text: "Option 3" });
});
