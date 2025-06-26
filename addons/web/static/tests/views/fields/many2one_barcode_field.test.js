import { beforeEach, expect, test } from "@odoo/hoot";
import { mockUserAgent, mockVibrate, runAllTimers } from "@odoo/hoot-mock";

import {
    clickSave,
    contains,
    defineModels,
    fields,
    getKwArgs,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import * as BarcodeScanner from "@web/core/barcode/barcode_dialog";

class Product extends models.Model {
    _name = "product.product";
    name = fields.Char();
    barcode = fields.Char();

    _records = [
        {
            id: 111,
            name: "product_cable_management_box",
            barcode: "601647855631",
        },
        {
            id: 112,
            name: "product_n95_mask",
            barcode: "601647855632",
        },
        {
            id: 113,
            name: "product_surgical_mask",
            barcode: "601647855633",
        },
    ];
    // to allow the search in barcode too
    name_search() {
        const result = super.name_search(...arguments);
        const kwargs = getKwArgs(arguments, "name", "domain");
        for (const record of this) {
            if (record.barcode === kwargs.name) {
                result.push([record.id, record.name]);
            }
        }
        return result;
    }
}

class SaleOrderLine extends models.Model {
    id = fields.Integer();
    product_id = fields.Many2one({
        relation: "product.product",
    });
}

defineModels([Product, SaleOrderLine]);

beforeEach(() => {
    mockUserAgent("android");
    mockVibrate((pattern) => expect.step(`vibrate:${pattern}`));
});

test("Many2OneBarcode component should display the barcode icon", async () => {
    await mountView({
        type: "form",
        resModel: "sale.order.line",
        arch: `
                <form>
                    <field name="product_id" widget="many2one_barcode"/>
                </form>
        `,
    });
    expect(".o_barcode").toHaveCount(1);
});

test("barcode button with single results", async () => {
    expect.assertions(3);

    // The product selected (mock) for the barcode scanner
    const selectedRecordTest = Product._records[0];

    patchWithCleanup(BarcodeScanner, {
        scanBarcode: async () => selectedRecordTest.barcode,
    });

    onRpc("sale.order.line", "web_save", (args) => {
        const selectedId = args.args[1]["product_id"];
        expect(selectedId).toBe(selectedRecordTest.id, {
            message: `product id selected ${selectedId}, should be ${selectedRecordTest.id} (${selectedRecordTest.barcode})`,
        });
        return args.parent();
    });

    await mountView({
        type: "form",
        resModel: "sale.order.line",
        arch: `
            <form>
                <field name="product_id" options="{'can_scan_barcode': True}"/>
            </form>
        `,
    });

    expect(".o_barcode").toHaveCount(1);

    await contains(".o_barcode").click();
    await clickSave();

    expect.verifySteps(["vibrate:100"]);
});

test.tags("desktop");
test("barcode button with multiple results", async () => {
    expect.assertions(5);

    // The product selected (mock) for the barcode scanner
    const selectedRecordTest = Product._records[1];

    patchWithCleanup(BarcodeScanner, {
        scanBarcode: async () => "mask",
    });

    onRpc("sale.order.line", "web_save", (args) => {
        const selectedId = args.args[1]["product_id"];
        expect(selectedId).toBe(selectedRecordTest.id, {
            message: `product id selected ${selectedId}, should be ${selectedRecordTest.id} (${selectedRecordTest.barcode})`,
        });
        return args.parent();
    });
    await mountView({
        type: "form",
        resModel: "sale.order.line",
        arch: `
            <form>
                <field name="product_id" options="{'can_scan_barcode': True}"/>
            </form>`,
    });

    expect(".o_barcode").toHaveCount(1);

    await contains(".o_barcode").click();
    await runAllTimers();
    expect(".o-autocomplete--dropdown-menu").toHaveCount(1);

    expect(
        ".o-autocomplete--dropdown-menu .o-autocomplete--dropdown-item.ui-menu-item:not(.o_m2o_dropdown_option)"
    ).toHaveCount(2);

    await contains(
        ".o-autocomplete--dropdown-menu .o-autocomplete--dropdown-item:nth-child(1)"
    ).click();
    await clickSave();
    expect.verifySteps(["vibrate:100"]);
});
