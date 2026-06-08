import { expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    bar = fields.Boolean({ default: true });

    _records = [{ id: 1, bar: true }];
}

defineModels([Partner]);

test.tags("mobile");
test("boolean_checkbox display as checkbox instead of toggle on mobile", async () => {
    await mountView({
        resModel: "partner",
        resId: 1,
        type: "form",
        arch: `<form><field widget="boolean_checkbox" name="bar"/></form>`,
    });
    expect(".o-checkbox").not.toHaveClass("o_boolean_toggle");
});
