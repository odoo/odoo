import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { clickSave, contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    _records = [{ id: 1, product_id: false }];

    product_id = fields.Many2one({ relation: "product" });
}

class Product extends models.Model {
    _records = [
        { id: 1, name: "a" },
        { id: 2, name: "b" },
        { id: 3, name: "c" },
    ];

    name = fields.Char();
}

defineModels([Partner, Product]);
defineMailModels();

test(`field is correctly renderered`, async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form><field name="product_id" widget="hr_holidays_radio_image"/></form>`,
    });
    expect(`.o_field_widget.o_field_hr_holidays_radio_image`).toHaveCount(1);
    expect(`.o_radio_input`).toHaveCount(3);
    expect(`.o_radio_input:checked`).toHaveCount(0);
    expect(`img`).toHaveCount(3);

    await contains(`img:eq(0)`).click();
    expect(`.o_radio_input:checked`).toHaveCount(1);

    await clickSave();
    expect(`.o_field_widget.o_field_hr_holidays_radio_image`).toHaveCount(1);
    expect(`.o_radio_input`).toHaveCount(3);
    expect(`.o_radio_input:checked`).toHaveCount(1);
    expect(`img`).toHaveCount(3);
});
