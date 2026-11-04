import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    char = fields.Char();
    model_name = fields.Char();

    _records = [
        { id: 1, char: "", model_name: "partner" },
        { id: 2, char: "", model_name: "partner" },
    ];

    _views = {
        form: /* xml */ `
            <form>
                <field name="char" widget="DynamicModelFieldSelectorChar" required="id == 1" readonly="id == 2" options="{'model': 'model_name'}"/>
            </form>
        `,
    };
}

defineModels([Partner]);

test("Dynamic model field selector char - required layout", async () => {
    await mountView({ type: "form", resModel: "partner", resId: 1 });
    await waitFor(".o_model_field_selector");
    expect(".o_model_field_selector_warning").toHaveCount(1);
    await contains(".o_model_field_selector_value").click();
    await contains(".o_model_field_selector_popover_item button:contains('Char')").click();
    await waitFor(".o_model_field_selector_value:contains('Char')");
    expect(".o_model_field_selector_warning").toHaveCount(0);
});

test("Dynamic model field selector char - readonly layout", async () => {
    await mountView({ type: "form", resModel: "partner", resId: 2 });
    await waitFor(".o_model_field_selector");
    expect(".o_model_field_selector_warning").toHaveCount(0);
    expect(".o_model_field_selector").toHaveClass("o_read_mode");
});
