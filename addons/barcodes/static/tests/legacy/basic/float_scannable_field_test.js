/** @odoo-module **/

import { nextTick, patchWithCleanup, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { barcodeGenericHandlers } from "@barcodes/barcode_handlers";
import { barcodeService } from "@barcodes/barcode_service";
import { simulateBarCode } from "../helpers";
import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";

const maxTimeBetweenKeysInMs = barcodeService.maxTimeBetweenKeysInMs;

let target;
let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        barcodeService.maxTimeBetweenKeysInMs = 0;
        registry.category("services").add("barcode", barcodeService, { force: true });
        registry
            .category("services")
            .add("barcode_autoclick", barcodeGenericHandlers, { force: true });

        serverData = {
            models: {
                product: {
                    fields: {
                        name: { string: "Product name", type: "char" },
                        float_field: { string: "Float", type: "float" },
                        float_field_2: { string: "Float", type: "float" },
                        barcode: { string: "Barcode", type: "char" },
                    },
                    records: [
                        { id: 1, name: "Large Cabinet", barcode: "1234567890" },
                        { id: 2, name: "Cabinet with Doors", barcode: "0987654321" },
                    ],
                },
            },
        };
        setupViewRegistries();
    });
    hooks.afterEach(() => {
        barcodeService.maxTimeBetweenKeysInMs = maxTimeBetweenKeysInMs;
    });

    QUnit.module("FloatScannableField");

    QUnit.test("widget field_float_scannable", async function (assert) {
        serverData.models.product.records[0].float_field = 4;

        const onBarcodeScanned = (event) => {
            assert.step(`barcode scanned ${event.detail.barcode}`);
        };

        const view = await makeView({
            type: "form",
            resModel: "product",
            serverData,
            resId: 1,
            arch: /*xml*/ `
                <form>
                    <field name="display_name"/>
                    <field name="float_field" widget="field_float_scannable"/>
                    <field name="float_field_2"/>
                </form>
            `,
        });
        view.env.services.barcode.bus.addEventListener("barcode_scanned", onBarcodeScanned);

        const inputDiv1 = target.querySelector(".o_field_widget[name=float_field]");
        assert.strictEqual(
            inputDiv1.querySelector("input").value,
            "4.00",
            "should display the correct value"
        );

        // we check here that a scan on the field_float_scannable widget triggers a
        // barcode event
        inputDiv1.querySelector("input").focus();
        simulateBarCode(["6", "0", "1", "6", "4", "7", "8", "5"], inputDiv1, "input");
        await nextTick();
        assert.verifySteps(["barcode scanned 60164785"]);
        assert.strictEqual(
            inputDiv1.querySelector("input"),
            document.activeElement,
            "float field should stay focused"
        );

        // we check here that a scan on the field without widget does not trigger a
        // barcode event
        const inputDiv2 = target.querySelector(".o_field_widget[name=float_field_2]");
        inputDiv2.querySelector("input").focus();
        simulateBarCode(["6", "0", "1", "6", "4", "7", "8", "5"], inputDiv2, "input");
        await nextTick();
        assert.verifySteps([]);

        view.env.services.barcode.bus.removeEventListener("barcode_scanned", onBarcodeScanned);
    });

    QUnit.test("do no update form twice after a command barcode scanned", async function (assert) {
        assert.expect(5);

        patchWithCleanup(FormController.prototype, {
            onPagerUpdate() {
                assert.step("update");
                return super.onPagerUpdate(...arguments);
            },
        });

        await makeView({
            type: "form",
            resModel: "product",
            serverData,
            arch: /*xml*/ `
                <form>
                    <field name="display_name"/>
                    <field name="float_field" widget="field_float_scannable"/>
                </form>
            `,
            mockRPC(_route, args) {
                if (args.method === "web_read") {
                    assert.step("web_read");
                }
            },
            resId: 1,
            resIds: [1, 2],
        });

        assert.verifySteps(["web_read"], "update should not have been called yet");

        // switch to next record
        simulateBarCode(
            ["O", "C", "D", "N", "E", "X", "T", "Enter"],
            document.activeElement
        );
        await nextTick();
        // a first update is done to reload the data (thus followed by a read), but
        // update shouldn't be called afterwards
        assert.verifySteps(["update", "web_read"]);
    });
});
