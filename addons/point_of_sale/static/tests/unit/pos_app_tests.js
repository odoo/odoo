/** @odoo-module */
import { Chrome } from "@point_of_sale/app/pos_app";
import { getFixture, mount } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { registry } from "@web/core/registry";
import { posService } from "@point_of_sale/app/store/pos_store";
import { numberBufferService } from "@point_of_sale/app/utils/number_buffer_service";
import { barcodeReaderService } from "@point_of_sale/app/barcode/barcode_reader_service";
import { EventBus } from "@odoo/owl";
import { uiService } from "@web/core/ui/ui_service";
import { dialogService } from "@web/core/dialog/dialog_service";
import { PosDataService } from "@point_of_sale/app/models/data_service";

const mockContextualUtilsService = {
    dependencies: ["pos", "localization"],
    start(env, { pos, localization }) {
        const formatCurrency = (value, hasSymbol = true) => {
            return "dummy";
        };
        const floatIsZero = (value) => {
            return value === 0;
        };
        env.utils = {
            formatCurrency,
            floatIsZero,
        };
    },
};

QUnit.module("Chrome", {
    beforeEach() {
        registry
            .category("services")
            .add("pos_data", PosDataService)
            .add("pos", posService)
            .add("number_buffer", numberBufferService)
            .add("barcode_reader", barcodeReaderService)
            .add("ui", uiService)
            .add("dialog", dialogService)
            .add("contextual_utils_service", mockContextualUtilsService)
            .add("barcode", {
                start() {
                    return { bus: new EventBus() };
                },
            })
            .add("bus_service", {
                start() {
                    return { addChannel: () => {}, subscribe: () => {} };
                },
            })
            .add("printer", {
                start() {
                    return { print: () => {} };
                },
            });

        for (const service of [
            "hardware_proxy",
            "debug",
            "notification",
            "sound",
            "action",
            "hotkey",
        ]) {
            registry.category("services").add(service, {
                start() {
                    return {};
                },
            });
        }
    },
});

export class MockPosData {
    get data() {
        return {
            models: {
                "product.product": { fields: {}, records: [] },
                "product.pricelist": { fields: {}, records: [] },
                "pos.session": {
                    fields: {},
                    records: [
                        {
                            name: "PoS Session",
                        },
                    ],
                },
                "res.company": {
                    fields: {
                        tax_calculation_rounding_method: {
                            string: "Tax rounding method",
                            type: "string",
                        },
                    },
                    records: [
                        {
                            tax_calculation_rounding_method: "round_globally",
                        },
                    ],
                },
                "res.partner": { fields: {}, records: [] },
                "stock.picking.type": { fields: {}, records: [] },
                "pos.config": {
                    fields: {
                        iface_printer: { string: "Iface printer", type: "boolean" },
                        trusted_config_ids: {
                            string: "Trusted config ids",
                            type: "many2many",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            name: "PoS Config",
                            iface_printer: false,
                            trusted_config_ids: [2],
                        },
                        {
                            id: 2,
                            name: "PoS Config 2",
                            iface_printer: true,
                            trusted_config_ids: [1],
                        },
                    ],
                },
                "pos.printer": { fields: {}, records: [] },
                "pos.payment.method": { fields: {}, records: [] },
                "res.currency": {
                    fields: { rounding: { string: "Rounding", type: "float" } },
                    records: [
                        {
                            rounding: 0.01,
                        },
                    ],
                },
                "res.users": {
                    fields: {},
                    records: [
                        {
                            id: 1,
                            name: "Administrator",
                        },
                    ],
                },
                "account.fiscal.position": { fields: {}, records: [] },
                "pos.category": { fields: {}, records: [] },
                "pos.order": { fields: {}, records: [] },
                "pos.order.line": { fields: {}, records: [] },
                "pos.payment": { fields: {}, records: [] },
                "pos.pack.operation.lot": { fields: {}, records: [] },
                "product.pricelist.item": { fields: {}, records: [] },
            },
        };
    }
}

QUnit.test("mount the Chrome", async (assert) => {
    const serverData = new MockPosData().data;
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
