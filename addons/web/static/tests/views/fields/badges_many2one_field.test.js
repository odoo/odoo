import { expect, queryAllTexts, test } from "@odoo/hoot";
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

    color = fields.Integer("color");
    icon = fields.Char("icon");

    _records = [
        { id: 37, display_name: "xphone", color: 6, icon: "fa-mobile" },
        { id: 41, display_name: "xpad", color: 7, icon: "fa-check" },
    ];
}

defineModels([Partner, Product]);

onRpc("has_group", () => true);

test("BadgesMany2OneField in a new record", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(`saved product_id: ${args[1]["product_id"]}`);
    });

    await mountView({
        resModel: "partner",
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

test("BadgesMany2OneField: verify icons are fetched via search_read and displayed", async () => {
    Product._records.push({ id: 1, display_name: "xmac" });

    onRpc("product", "search_read", ({ kwargs }) => {
        expect.step("search_read_triggered");
        expect(kwargs.fields).toInclude("icon");
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="product_id" widget="badges_many2one"
                    options="{'default_icon': 'fa-cog', 'related_icon_field': 'icon'}"/>
            </form>`,
    });

    // Check if icons are rendered
    expect("span.o_selection_badge:eq(0) span.fa-cog").toHaveCount(1);
    expect("span.o_selection_badge:eq(1) span.fa-mobile").toHaveCount(1);
    expect("span.o_selection_badge:eq(2) span.fa-check").toHaveCount(1);

    expect.verifySteps(["search_read_triggered"]);
});

test("BadgesMany2OneField: unchecking selected value (required field)", async () => {
    Partner._fields.product_id.required = true;
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: '<form><field name="product_id" widget="badges_many2one"/></form>',
    });
    expect("span.o_selection_badge").toHaveCount(2, { message: "should have 2 possible choices" });
    expect("span.o_selection_badge.active").toHaveCount(1, { message: "one is active" });
    expect("span.o_selection_badge.active").toHaveText("xphone", {
        message: "the active one should be xphone",
    });
    // click again on the active badge - it should NOT deselect since field is required
    await contains("span.o_selection_badge.active").click();
    expect("span.o_selection_badge.active").toHaveCount(1, {
        message: "active badge should remain selected for required field",
    });
});

test("BadgesMany2OneField: with domain and badge_limit option", async () => {
    Partner._fields.product_min_id = fields.Integer({ default: 20 });
    Product._records.push({ id: 1, display_name: "xmac" });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="product_min_id"/>
                <field name="product_id" widget="badges_many2one"
                    domain="[['id', '>', product_min_id]]"
                    options="{'badge_limit': 2}"/>
            </form>`,
    });

    expect("span.o_selection_badge").toHaveCount(2);
    expect(".o_select_menu").toHaveCount(0);

    await contains(".o_field_widget[name=product_min_id] input").edit("0");
    expect("span.o_selection_badge").toHaveCount(0);
    expect(".o_select_menu").toHaveCount(1);

    await contains(".o_select_menu_input").click();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["xmac", "xpad", "xphone"]);
});

test("BadgesMany2OneField: placeholder attribute is used when provided", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="product_id" widget="badges_many2one"
                    options="{'badge_limit': 1}"
                    placeholder="Pick a product"/>
            </form>`,
    });

    expect(
        ".o_select_menu .dropdown-toggle .o_select_menu_input[placeholder='Pick a product']"
    ).toHaveCount(1, {
        message: "should display the custom placeholder",
    });
});

test("BadgesMany2OneField: placeholder falls back to field label when not provided", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="product_id" widget="badges_many2one"
                    options="{'badge_limit': 1}"/>
            </form>`,
    });

    expect(
        ".o_select_menu .dropdown-toggle .o_select_menu_input[placeholder='Product']"
    ).toHaveCount(1, {
        message: "should fall back to the field label as placeholder",
    });
});

test("[Offline] BadgesMany2OneField: verify badges are displayed in offline mode", async () => {
    onRpc("product", "name_search", () => {
        expect.step("name_search");
        return new Response("", { status: 502 });
    });
    await mountView({
        resModel: "partner",
        resId: 2,
        type: "form",
        arch: `
            <form>
                <field name="product_id" widget="badges_many2one"/>
            </form>`,
    });

    // Verify the field doesn't crash and displays the fallback name
    expect(".o_selection_badge").toHaveCount(1);
    expect(".o_selection_badge:contains(xphone)").toHaveCount(1);

    expect.verifySteps([
        "name_search", // initial rendering
        "name_search", // re-rendered because we switched offline (due to the first name_search)
    ]);
});
