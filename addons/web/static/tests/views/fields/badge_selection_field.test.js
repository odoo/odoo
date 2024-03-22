import { expect, test } from "@odoo/hoot";
import {
    clickSave,
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    _name = "res.partner";

    product_id = fields.Many2one({ relation: "product" });
    color = fields.Selection({
        selection: [
            ["red", "Red"],
            ["black", "Black"],
        ],
        default: "red",
    });

    _records = [{ id: 1 }, { id: 2, product_id: 37 }];
}

class Product extends models.Model {
    _rec_name = "display_name";

    _records = [
        { id: 37, display_name: "xphone" },
        { id: 41, display_name: "xpad" },
    ];
}

defineModels([Partner, Product]);

test("BadgeSelectionField widget on a many2one in a new record", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(`saved product_id: ${args[1]["product_id"]}`);
    });

    await mountView({
        resModel: "res.partner",
        type: "form",
        arch: `<form><field name="product_id" widget="selection_badge"/></form>`,
    });

    expect(`div.o_field_selection_badge`).toHaveCount(1, {
        message: "should have rendered outer div",
    });
    expect(`span.o_selection_badge`).toHaveCount(2, { message: "should have 2 possible choices" });
    expect(`span.o_selection_badge:contains(xphone)`).toHaveCount(1, {
        message: "one of them should be xphone",
    });
    expect(`span.active`).toHaveCount(0, { message: "none of the input should be checked" });

    await contains(`span.o_selection_badge`).click();
    expect(`span.active`).toHaveCount(1, { message: "one of the input should be checked" });

    await clickSave();
    expect(["saved product_id: 37"]).toVerifySteps();
});

test("BadgeSelectionField widget on a selection in a new record", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(`saved color: ${args[1]["color"]}`);
    });
    await mountView({
        resModel: "res.partner",
        type: "form",
        arch: `<form><field name="color" widget="selection_badge"/></form>`,
    });

    expect(`div.o_field_selection_badge`).toHaveCount(1, {
        message: "should have rendered outer div",
    });
    expect("span.o_selection_badge").toHaveCount(2, { message: "should have 2 possible choices" });
    expect(`span.o_selection_badge:contains(Red)`).toHaveCount(1, {
        message: "one of them should be Red",
    });

    await contains(`span.o_selection_badge:last`).click();
    await clickSave();
    expect(["saved color: black"]).toVerifySteps();
});

test("BadgeSelectionField widget on a selection in a readonly mode", async () => {
    await mountView({
        resModel: "res.partner",
        type: "form",
        arch: `<form><field name="color" widget="selection_badge" readonly="1"/></form>`,
    });
    expect(`div.o_readonly_modifier span`).toHaveCount(1, {
        message: "should have 1 possible value in readonly mode",
    });
});
