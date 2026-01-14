import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
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
    allowed_colors = fields.Json();

    product_color_id = fields.Integer({
        relation: "product",
        related: "product_id.color",
        default: 20,
    });

    _records = [
        { id: 1 },
        { id: 2, allowed_colors: "['red']", product_id: 37, product_color_id: 6 },
    ];
}

class Product extends models.Model {
    _rec_name = "display_name";

    name = fields.Char("name");
    color = fields.Integer("color");
    icon = fields.Char("icon");

    _records = [
        { id: 37, display_name: "xphone", name: "xphone", color: 6, icon: "fa-mobile" },
        { id: 41, display_name: "xpad", name: "xpad", color: 7, icon: "fa-check" },
    ];
}

defineModels([Partner, Product]);

onRpc("has_group", () => true);

test("BadgeSelectionField widget on a many2one in a new record", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(`saved product_id: ${args[1]["product_id"]}`);
    });

    await mountView({
        resModel: "res.partner",
        type: "form",
        arch: `<form><field name="product_id" widget="badges_many2one"/></form>`,
    });

    expect(`div.o_field_badges_many2one`).toHaveCount(1, {
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
    expect.verifySteps(["saved product_id: 37"]);
});

test("[Offline] BadgeSelectionField widget on a many2one", async () => {
    onRpc("product", "name_search", () => new Response("", { status: 502 }));
    await mountView({
        resModel: "res.partner",
        resId: 2,
        type: "form",
        arch: `<form><field name="product_id" widget="badges_many2one"/></form>`,
    });

    expect(`div.o_field_badges_many2one`).toHaveCount(1, {
        message: "should have rendered outer div",
    });
    expect(`div.o_field_badges_many2one span`).toHaveCount(1);
    expect(queryAllTexts(`div.o_field_badges_many2one span`)).toEqual(["xphone"]);
});

test("BadgeSelectionField: verify icons are fetched via search_read and displayed", async () => {
    onRpc("product", "search_read", ({ kwargs }) => {
        expect.step("search_read_triggered");
        expect(kwargs.fields).toInclude("icon");
    });

    await mountView({
        resModel: "res.partner",
        type: "form",
        arch: `
            <form>
                <field name="product_id" widget="badges_many2one" options="{'related_icon_field': 'icon'}"/>
            </form>`,
    });

    // Check if icons are rendered
    expect("span.o_selection_badge:eq(0) span.fa-mobile").toHaveCount(1);
    expect("span.o_selection_badge:eq(1) span.fa-check").toHaveCount(1);

    expect.verifySteps(["search_read_triggered"]);
});

test("[Offline] BadgeSelectionField: verify badges are displayed in offline mode", async () => {
    onRpc("product", "search_read", () => {
        throw new Response("", { status: 502 });
    });
    await mountView({
        resModel: "res.partner",
        resId: 2,
        type: "form",
        arch: `
                <form>
                    <field name="product_id" widget="badges_many2one"/>
                </form>`,
    });

    // Verify the field doesn't crash and displays the fallback name
    expect("span.o_selection_badge").toHaveCount(2);
    expect("span.o_selection_badge:contains(xphone)").toHaveCount(1);
});
