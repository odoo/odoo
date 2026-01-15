import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    editSelectMenu,
    fields,
    models,
    mountView,
} from "@web/../tests/web_test_helpers";

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
    await contains(".o_field_widget[name='type'] input").click();
    expect(`.o_select_menu_item`).toHaveCount(2);
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Coupons", "Promotion"]);
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
    await contains(".o_field_widget[name='type'] input").click();
    expect(`.o_select_menu_item`).toHaveCount(2);
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Coupons", "Promotion"]);
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
    await contains(".o_field_widget[name='type'] input").click();
    expect(`.o_select_menu_item`).toHaveCount(3);
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Coupons", "Promotion", "Gift card"]);
    await editSelectMenu(".o_field_widget[name='type'] input", { value: "Coupons" });
    await contains(".o_field_widget[name='type'] input").click();
    expect(`.o_select_menu_item`).toHaveCount(2);
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Coupons", "Promotion"]);
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
    await contains(".o_field_widget[name='type'] input").click();
    expect(`.o_select_menu_item`).toHaveCount(2);
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Coupons", "Promotion"]);
});
