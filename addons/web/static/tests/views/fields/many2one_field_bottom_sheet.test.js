import { animationFrame, expect, queryAllTexts, runAllTimers, test } from "@odoo/hoot";
import { mockUserAgent } from "@odoo/hoot-mock";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    product_id = fields.Many2one({ string: "Product", relation: "product" });

    _records = [{ id: 1, product_id: 37 }];
}

class Product extends models.Model {
    name = fields.Char();

    _records = [
        { id: 37, name: "xphone" },
        { id: 41, name: "xpad" },
    ];
}

defineModels([Partner, Product]);

test.tags("mobile");
test("bottom_sheet option: pick the value in a bottom sheet", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form><field name="product_id" options="{'bottom_sheet': True}"/></form>`,
    });
    expect(".o_field_many2one input").toHaveValue("xphone");

    await contains(".o_field_many2one input").click();
    expect(".o_bottom_sheet").toHaveCount(1);
    expect(queryAllTexts(".o_bottom_sheet .dropdown-item")).toEqual(["xphone", "xpad"]);
    expect(".o_bottom_sheet .dropdown-item.selected").toHaveText("xphone");

    await contains(".o_bottom_sheet .dropdown-item:contains(xpad)").click();
    await runAllTimers();
    await animationFrame();
    expect(".o_bottom_sheet").toHaveCount(0);
    expect(".o_field_many2one input").toHaveValue("xpad");
});

test.tags("mobile");
test("bottom_sheet option: the options follow the field domain", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="product_id" domain="[('name', '=', 'xpad')]" options="{'bottom_sheet': True}"/>
            </form>`,
    });

    await contains(".o_field_many2one input").click();
    expect(queryAllTexts(".o_bottom_sheet .dropdown-item")).toEqual(["xpad"]);
});

test.tags("mobile");
test("bottom_sheet option: no matching record", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="product_id" domain="[('id', '=', 0)]" options="{'bottom_sheet': True}"/>
            </form>`,
    });

    await contains(".o_field_many2one input").click();
    expect(".o_bottom_sheet .dropdown-item").toHaveCount(0);
    expect(".o_bottom_sheet").toHaveText("No records");
});

test.tags("mobile");
test("bottom_sheet option: the internal link stays next to the field", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form><field name="product_id" options="{'bottom_sheet': True}"/></form>`,
    });
    expect(".o_field_many2one .o_external_button").toHaveCount(1);

    await contains(".o_field_many2one input").click();
    expect(".o_bottom_sheet .o_external_button").toHaveCount(0);
});

test.tags("mobile");
test("bottom_sheet option: no barcode button", async () => {
    mockUserAgent("android");
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="product_id" options="{'can_scan_barcode': True}"/>
                <field name="product_id" options="{'can_scan_barcode': True, 'bottom_sheet': True}"/>
            </form>`,
    });
    expect(".o_field_many2one:eq(0) .o_barcode").toHaveCount(1);
    expect(".o_field_many2one:eq(1) .o_barcode").toHaveCount(0);

    await contains(".o_field_many2one:eq(1) input").click();
    expect(".o_bottom_sheet").toHaveCount(1);
    expect(".o_bottom_sheet .o_barcode").toHaveCount(0);
});

test.tags("desktop");
test("bottom_sheet option is ignored on desktop", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form><field name="product_id" options="{'bottom_sheet': True}"/></form>`,
    });

    await contains(".o_field_many2one input").click();
    await runAllTimers();
    expect(".o_bottom_sheet").toHaveCount(0);
    expect(".o_field_many2one .o-autocomplete--dropdown-menu").toHaveCount(1);
});
