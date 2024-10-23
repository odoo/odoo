import { expect, test } from "@odoo/hoot";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Program extends models.Model {
    type = fields.Selection({
        required: true,
        selection: [
            ["coupon", "Coupons"],
            ["promotion", "Promotion"],
            ["gift_card", "Gift card"],
        ],
    });
    available_types = fields.Json({
        required: true,
    });

    _records = [
        { id: 1, type: "coupon", available_types: "['coupon', 'promotion']" },
        { id: 2, type: "gift_card", available_types: "['gift_card', 'promotion']" },
    ];
}
defineModels([Program]);

// Note: the `toHaveCount` always check for one more as there will be an invisible empty option every time.

test(`FilterableSelectionField test whitelist`, async () => {
    await mountView({
        resModel: "program",
        type: "form",
        arch: `
            <form>
                <field name="type" widget="filterable_selection" options="{'whitelisted_values': ['coupons', 'promotion']}"/>
            </form>
        `,
        resId: 1,
    });
    expect(`select option`).toHaveCount(3);
    expect(`.o_field_widget[name="type"] select option[value='"coupon"']`).toHaveCount(1);
    expect(`.o_field_widget[name="type"] select option[value='"promotion"']`).toHaveCount(1);
});

test(`FilterableSelectionField test blacklist`, async () => {
    await mountView({
        resModel: "program",
        type: "form",
        arch: `
            <form>
                <field name="type" widget="filterable_selection" options="{'blacklisted_values': ['gift_card']}"/>
            </form>
        `,
        resId: 1,
    });
    expect(`select option`).toHaveCount(3);
    expect(`.o_field_widget[name="type"] select option[value='"coupon"']`).toHaveCount(1);
    expect(`.o_field_widget[name="type"] select option[value='"promotion"']`).toHaveCount(1);
});

test(`FilterableSelectionField test with invalid value`, async () => {
    // The field should still display the current value in the list
    await mountView({
        resModel: "program",
        type: "form",
        arch: `
            <form>
                <field name="type" widget="filterable_selection" options="{'blacklisted_values': ['gift_card']}"/>
            </form>
        `,
        resId: 2,
    });
    expect(`select option`).toHaveCount(4);
    expect(`.o_field_widget[name="type"] select option[value='"gift_card"']`).toHaveCount(1);
    expect(`.o_field_widget[name="type"] select option[value='"coupon"']`).toHaveCount(1);
    expect(`.o_field_widget[name="type"] select option[value='"promotion"']`).toHaveCount(1);

    await contains(`.o_field_widget[name="type"] select`).select(`"coupon"`);
    expect(`select option`).toHaveCount(3);
    expect(`.o_field_widget[name="type"] select option[value='"gift_card"']`).toHaveCount(0);
    expect(`.o_field_widget[name="type"] select option[value='"coupon"']`).toHaveCount(1);
    expect(`.o_field_widget[name="type"] select option[value='"promotion"']`).toHaveCount(1);
});

test(`FilterableSelectionField test whitelist_fname`, async () => {
    await mountView({
        resModel: "program",
        type: "form",
        arch: `
            <form>
                <field name="available_types" invisible="1"/>
                <field name="type" widget="filterable_selection" options="{'whitelist_fname': 'available_types'}"/>
            </form>
        `,
        resId: 1,
    });
    expect(`select option`).toHaveCount(3);
    expect(`.o_field_widget[name="type"] select option[value='"coupon"']`).toHaveCount(1);
    expect(`.o_field_widget[name="type"] select option[value='"promotion"']`).toHaveCount(1);
});
