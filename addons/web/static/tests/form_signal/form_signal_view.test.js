import { expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    name = fields.Char();

    _records = [{ id: 1, name: "first record" }];
}

defineModels([Partner]);

test("form_signal renders hello world", async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form js_class="form_signal"><field name="name"/></form>`,
        resId: 1,
    });
    expect("h1").toHaveText("Hello world");
    expect(".o_content p").toHaveText("partner, record 1");
});
