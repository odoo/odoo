/** @odoo-module **/

import { beforeEach, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { FormController } from "@web/views/form/form_controller";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { barcodeService } from "@barcodes/barcode_service";
import { press } from "@odoo/hoot-dom";

async function simulateBarCode(chars) {
    for (const char of chars) {
        await press(char);
    }
}
class Product extends models.Model {
    name = fields.Char({ string: "Product name" });
    float_field = fields.Float({ string: "Float" });
    float_field_2 = fields.Float({ string: "Float" });
    barcode = fields.Char({ string: "Barcode" });
    _records = [
        { id: 1, name: "Large Cabinet", barcode: "1234567890" },
        { id: 2, name: "Cabinet with Doors", barcode: "0987654321" },
    ];
}

defineModels([Product]);

beforeEach(() => {
    patchWithCleanup(barcodeService, {
        maxTimeBetweenKeysInMs: 0,
    });
});

test.tags("mobile");
test("widget field_float_scannable", async () => {
    Product._records[0].float_field = 4;

    const onBarcodeScanned = (event) => {
        expect.step(`barcode scanned ${event.detail.barcode}`);
    };

    const view = await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: /*xml*/ `
            <form>press
                <field name="display_name"/>
                <field name="float_field" widget="field_float_scannable"/>
                <field name="float_field_2"/>
            </form>
        `,
    });
    view.env.services.barcode.bus.addEventListener("barcode_scanned", onBarcodeScanned);

    expect(".o_field_widget[name=float_field] input").toHaveValue("4.00");

    // we check here that a scan on the field_float_scannable widget triggers a
    // barcode event
    await contains(".o_field_widget[name=float_field] input").focus();
    await simulateBarCode(["6", "0", "1", "6", "4", "7", "8", "5"]);
    await animationFrame();
    expect.verifySteps(["barcode scanned 60164785"]);
    expect(".o_field_widget[name=float_field] input").toBeFocused();

    // we check here that a scan on the field without widget does not trigger a
    // barcode event
    await contains(".o_field_widget[name=float_field_2] input").focus();
    await simulateBarCode(["6", "0", "1", "6", "4", "7", "8", "5"]);
    await animationFrame();
    expect.verifySteps([]);

    view.env.services.barcode.bus.removeEventListener("barcode_scanned", onBarcodeScanned);
});

test.tags("mobile");
test("do no update form twice after a command barcode scanned", async () => {
    patchWithCleanup(FormController.prototype, {
        onPagerUpdate(...args) {
            expect.step("update");
            super.onPagerUpdate(...args);
        },
    });

    onRpc("web_read", () => {
        expect.step("web_read");
    });

    await mountView({
        type: "form",
        resModel: "product",
        arch: /*xml*/ `
            <form>
                <field name="display_name"/>
                <field name="float_field" widget="field_float_scannable"/>
            </form>
        `,
        resId: 1,
        resIds: [1, 2],
    });

    expect.verifySteps(["web_read"]);

    // switch to next record
    await simulateBarCode(["O", "C", "D", "N", "E", "X", "T", "Enter"]);

    // a first update is done to reload the data (thus followed by a read), but
    // update shouldn't be called afterwards
    expect.verifySteps(["update", "web_read"]);
});
