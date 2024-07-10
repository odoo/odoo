/** @odoo-module */
/* global posmodel */
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
import { RPCError } from "@web/core/network/rpc";

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
            .add("alert", {
                start() {
                    return { add: () => {}, dismiss: () => {} };
                },
            })
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
            "popover",
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
                "product.product": { relations: {}, fields: {}, data: [] },
                "product.pricelist": { relations: {}, fields: {}, data: [] },
                "pos.session": {
                    relations: {},
                    fields: {},
                    data: [
                        {
                            name: "PoS Session",
                            id: 1,
                        },
                    ],
                },
                "res.company": {
                    relations: {},
                    fields: {
                        tax_calculation_rounding_method: {
                            string: "Tax rounding method",
                            type: "string",
                        },
                    },
                    data: [
                        {
                            tax_calculation_rounding_method: "round_globally",
                        },
                    ],
                },
                "res.partner": {
                    relations: {},
                    fields: {
                        vat: {
                            string: "VAT",
                            type: "string",
                        },
                    },
                    data: [],
                },
                "stock.picking.type": { relations: {}, fields: {}, data: [] },
                "pos.config": {
                    relations: {},
                    fields: {
                        iface_printer: {
                            string: "Iface printer",
                            type: "boolean",
                        },
                        trusted_config_ids: {
                            string: "Trusted config ids",
                            type: "many2many",
                        },
                    },
                    data: [
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
                "pos.printer": { relations: {}, fields: {}, data: [] },
                "pos.payment.method": { relations: {}, fields: {}, data: [] },
                "res.currency": {
                    relations: {},
                    fields: {
                        rounding: {
                            string: "Rounding",
                            type: "float",
                        },
                    },
                    data: [
                        {
                            rounding: 0.01,
                        },
                    ],
                },
                "res.users": {
                    relations: {},
                    fields: {},
                    data: [
                        {
                            id: 1,
                            name: "Administrator",
                        },
                    ],
                },
                "account.fiscal.position": { relations: {}, fields: {}, data: [] },
                "pos.category": { relations: {}, fields: {}, data: [] },
                "pos.order": { relations: {}, fields: {}, data: [] },
                "pos.order.line": { relations: {}, fields: {}, data: [] },
                "pos.payment": { relations: {}, fields: {}, data: [] },
                "pos.pack.operation.lot": { relations: {}, fields: {}, data: [] },
                "product.pricelist.item": { relations: {}, fields: {}, data: [] },
                "product.attribute.custom.value": { relations: {}, fields: {}, data: [] },
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

QUnit.test("test unsynch data error filtering", async (assert) => {
    const serverData = new MockPosData().data;
    const fixture = getFixture();
    assert.verifySteps([]);
    const testEnv = await makeTestEnv({
        serverData,
        async mockRPC(route, args) {
            if (route === "/web/dataset/call_kw/res.partner/create") {
                const error = new RPCError();
                error.exceptionName = "odoo.exceptions.ValidationError";
                error.code = 200;
                throw error;
            }
        },
    });
    await mount(Chrome, fixture, {
        env: testEnv,
        test: true,
        props: { disableLoader: () => {} },
    });
    const partner_data = {
        name: "Test 1",
        vat: "BE40301926",
    };
    try {
        await posmodel.data.create("res.partner", [partner_data]);
    } catch {
        assert.step("create failed");
        assert.equal(posmodel.data.network.unsyncData.length, 0);
    }
    assert.verifySteps(["create failed"]);
});
