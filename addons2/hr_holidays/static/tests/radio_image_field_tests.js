/** @odoo-module **/

import { click, clickSave } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;

QUnit.module("radio image field", {
    beforeEach() {
        serverData = {
            models: {
                partner: {
                    fields: {
                        product_id: { string: "Product", type: "many2one", relation: "product" },
                    },
                    records: [{ id: 1, product_id: false }],
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char" },
                    },
                    records: [
                        { id: 1, display_name: "a" },
                        { id: 2, display_name: "b" },
                        { id: 3, display_name: "c" },
                    ],
                },
            },
        };
        setupViewRegistries();
    },
});

QUnit.test("field is correctly renderered", async (assert) => {
    await makeView({
        type: "form",
        resModel: "partner",
        resId: 1,
        serverData,
        arch: '<form><field name="product_id" widget="hr_holidays_radio_image"/></form>',
    });
    assert.containsOnce($, ".o_field_widget.o_field_hr_holidays_radio_image");
    assert.containsN($, ".o_radio_input", 3);
    assert.containsNone($, ".o_radio_input:checked");
    assert.containsN($, "img", 3);

    await click($("img")[0]);
    assert.containsOnce($, ".o_radio_input:checked");

    await clickSave(document.body);
    assert.containsOnce($, ".o_field_widget.o_field_hr_holidays_radio_image");
    assert.containsN($, ".o_radio_input", 3);
    assert.containsN($, "img", 3);
});
