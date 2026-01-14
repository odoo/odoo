import { expect, test } from "@odoo/hoot";
import { animationFrame, queryAllTexts } from "@odoo/hoot-dom";
import {
    clickSave,
    contains,
    defineModels,
    fields,
    MockServer,
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
    expect("div.o_field_badges_many2one").toHaveCount(1, {
        message: "should have rendered outer div",
    });
    expect("span.o_selection_badge").toHaveCount(2, { message: "should have 2 possible choices" });
    expect("span.o_selection_badge:contains(xphone)").toHaveCount(1, {
        message: "one of them should be xphone",
    });
    expect("span.active").toHaveCount(0, { message: "none of the input should be checked" });
    await contains("span.o_selection_badge").click();
    expect("span.active").toHaveCount(1, { message: "one of the input should be checked" });
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
    expect("div.o_field_badges_many2one").toHaveCount(1, {
        message: "should have rendered outer div",
    });
    expect("div.o_field_badges_many2one span").toHaveCount(1);
    expect(queryAllTexts("div.o_field_badges_many2one span")).toEqual(["xphone"]);
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

test("BadgeSelectionField widget on a selection in a new record", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(`saved color: ${args[1]["color"]}`);
    });
    await mountView({
        resModel: "res.partner",
        type: "form",
        arch: `<form><field name="color" widget="badges_selection"/></form>`,
    });
    expect("div.o_field_badges_selection").toHaveCount(1, {
        message: "should have rendered outer div",
    });
    expect("span.o_selection_badge").toHaveCount(2, { message: "should have 2 possible choices" });
    expect("span.o_selection_badge:contains(Red)").toHaveCount(1, {
        message: "one of them should be Red",
    });
    await contains("span.o_selection_badge:last").click();
    await clickSave();
    expect.verifySteps(["saved color: black"]);
});

test("BadgeSelectionField widget on a selection in a readonly mode", async () => {
    await mountView({
        resModel: "res.partner",
        type: "form",
        arch: `<form><field name="color" widget="badges_selection" readonly="1"/></form>`,
    });
    expect("div.o_readonly_modifier span").toHaveCount(1, {
        message: "should have 1 possible value in readonly mode",
    });
});

test("BadgeSelectionField widget on a selection unchecking selected value", async () => {
    onRpc("res.partner", "web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1]).toEqual({ color: false });
    });
    await mountView({
        type: "form",
        resModel: "res.partner",
        arch: '<form><field name="color" widget="badges_selection"/></form>',
    });
    expect("div.o_field_badges_selection").toHaveCount(1, {
        message: "should have rendered outer div",
    });
    expect("span.o_selection_badge").toHaveCount(2, { message: "should have 2 possible choices" });
    expect("span.o_selection_badge.active").toHaveCount(1, { message: "one is active" });
    expect("span.o_selection_badge.active").toHaveText("Red", {
        message: "the active one should be Red",
    });
    // click again on red option and save to update the server data
    await contains("span.o_selection_badge.active").click();
    expect.verifySteps([]);
    await contains(".o_form_button_save").click();
    expect.verifySteps(["web_save"]);
    expect(MockServer.env["res.partner"].at(-1).color).toBe(false, {
        message: "the new value should be false as we have selected same value as default",
    });
});

test("BadgeSelectionField widget on a selection unchecking selected value (required field)", async () => {
    Partner._fields.color.required = true;
    onRpc("res.partner", "web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1]).toEqual({ color: "red" });
    });
    await mountView({
        type: "form",
        resModel: "res.partner",
        arch: '<form><field name="color" widget="badges_selection"/></form>',
    });
    expect("div.o_field_badges_selection").toHaveCount(1, {
        message: "should have rendered outer div",
    });
    expect("span.o_selection_badge").toHaveCount(2, { message: "should have 2 possible choices" });
    expect("span.o_selection_badge.active").toHaveCount(1, { message: "one is active" });
    expect("span.o_selection_badge.active").toHaveText("Red", {
        message: "the active one should be Red",
    });
    // click again on red option and save to update the server data
    await contains("span.o_selection_badge.active").click();
    expect.verifySteps([]);
    await contains(".o_form_button_save").click();
    expect.verifySteps(["web_save"]);
    expect(MockServer.env["res.partner"].at(-1).color).toBe("red", {
        message: "the new value should be red",
    });
});

test("BadgeSelectionField: selection type with icon_mapping", async () => {
    await mountView({
        resModel: "res.partner",
        type: "form",
        arch: `
            <form>
                <field name="color" widget="badges_selection" options="{
                    'icon_mapping': {'black': 'fa-moon-o', 'red': 'fa-sun-o'}
                }"/>
            </form>`,
    });
    // 'black' should use the mapping
    expect("span.o_selection_badge:contains(Black) span.fa-moon-o").toHaveCount(1);
    // 'red' should use the mapping
    expect("span.o_selection_badge:contains(Red) span.fa-sun-o").toHaveCount(1);
});

test("BadgeSelectionField: switching to SelectMenu when badgeLimit is exceeded", async () => {
    await mountView({
        resModel: "res.partner",
        type: "form",
        arch: `
            <form>
                <field id="color" name="color" widget="badges_selection" options="{'badgeLimit': 1}"/>
            </form>`,
    });
    // Since Partner.color has 2 options and badgeLimit is 1, it should show a dropdown
    expect(".o_select_menu").toHaveCount(1, {
        message: "Should render SelectMenu instead of badges",
    });
    expect("span.o_selection_badge").toHaveCount(0, {
        message: "Should not render individual badges",
    });
    // Open dropdown and check values
    await contains(".o_select_menu input").click();
    await animationFrame();
    expect(".o-dropdown-item").toHaveCount(2);
});

test("BadgeSelectionField: verify options are filtered via the allowed_selection_field option", async () => {
    await mountView({
        resModel: "res.partner",
        resId: 2,
        type: "form",
        arch: `
            <form>
                <field name="allowed_colors" invisible="1"/>
                <field name="color" widget="badges_selection" 
                    options="{'allowed_selection_field': 'allowed_colors'}"
                />
            </form>`,
    });
    // Verify only the filtered option is rendered
    expect("span.o_selection_badge:contains(Red)").toHaveCount(1);
    // Verify that the total number of badges is ONLY 1
    expect("span.o_selection_badge").toHaveCount(1);
});
