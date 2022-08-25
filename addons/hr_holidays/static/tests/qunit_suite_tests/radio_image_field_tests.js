/** @odoo-module **/

import { click, clickEdit, clickSave, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
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
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.module("RadioImageField");

    QUnit.test("field is correctly renderered", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form><field name="product_id" widget="hr_holidays_radio_image"/></form>',
        });
        assert.containsOnce(target, ".o_field_widget.o_field_hr_holidays_radio_image");
        assert.containsNone(target, ".o_radio_input");
        assert.containsNone(target, "img");

        await clickEdit(target);

        assert.containsOnce(target, ".o_field_widget.o_field_hr_holidays_radio_image");
        assert.containsN(target, ".o_radio_input", 3);
        assert.containsNone(target, ".o_radio_input:checked");
        assert.containsN(target, "img", 3);

        await click(target.querySelector("img"));
        assert.containsOnce(target, ".o_radio_input:checked");

        await clickSave(target);
        assert.containsOnce(target, ".o_field_widget.o_field_hr_holidays_radio_image");
        assert.containsNone(target, ".o_radio_input");
        assert.containsOnce(target, "img", 1);
    });
});
