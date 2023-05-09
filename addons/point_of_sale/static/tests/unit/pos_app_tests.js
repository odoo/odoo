/** @odoo-module */
import { Chrome } from "@point_of_sale/js/Chrome";
import { getFixture, mount } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { registry } from "@web/core/registry";
import { posService } from "@point_of_sale/app/pos_store";
import { numberBufferService } from "@point_of_sale/app/number_buffer_service";
import { barcodeReaderService } from "@point_of_sale/app/barcode_reader_service";
import { EventBus } from "@odoo/owl";
import { uiService } from "@web/core/ui/ui_service";

QUnit.module("Chrome", {
    beforeEach() {
        registry
            .category("services")
            .add("pos", posService)
            .add("number_buffer", numberBufferService)
            .add("barcode_reader", barcodeReaderService)
            .add("ui", uiService)
            .add("barcode", {
                start() {
                    return { bus: new EventBus() };
                },
            })
            .add("bus_service", {
                start() {
                    return { addChannel: () => {}, addEventListener: () => {} };
                },
            });

        for (const service of [
            "popup",
            "hardware_proxy",
            "debug",
            "pos_notification",
            "sound",
            "action",
        ]) {
            registry.category("services").add(service, {
                start() {
                    return {};
                },
            });
        }
    },
});

const serverData = {
    models: { "product.product": { fields: {}, records: [] } },
};

QUnit.test("mount the Chrome", async (assert) => {
    const fixture = getFixture();
    assert.verifySteps([]);
    await mount(Chrome, fixture, {
        env: await makeTestEnv({ serverData }),
        test: true,
        props: { disableLoader: () => assert.step("disable loader") },
    });
    assert.containsOnce(fixture, ".pos");
    assert.verifySteps(["disable loader"]);
});
