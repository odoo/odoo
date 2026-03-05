import { uuidv4 } from "@point_of_sale/utils";
import {
    getService,
    onRpc,
    patchWithCleanup,
    MockServer,
    mountWithCleanup,
    makeDialogMockEnv,
} from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { registry } from "@web/core/registry";
import { selfOrderIndex } from "@pos_self_order/app/self_order_index";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { unpatchSelf } from "@pos_self_order/app/services/data_service";

export function initMockRpc() {
    onRpc("/pos-self/relations/1", () =>
        MockServer.env["pos.session"].load_data_params({ self_ordering: true })
    );
    onRpc("/pos-self/data/1", () =>
        MockServer.env["pos.session"].load_data({ self_ordering: true })
    );
    onRpc("/pos-self/receipt-template/1", () => []);

    const mockProcssOrder = async (request) => {
        const { params } = await request.json();
        const response = MockServer.env["pos.order"].sync_from_ui([params.order]);
        const models = MockServer.env["pos.session"]._load_self_data_models();
        return Object.fromEntries(Object.entries(response).filter(([key]) => models.includes(key)));
    };

    const mockSyncOrder = async (request) => {
        const { params } = await request.json();
        const { order } = params;
        const configId = order.config_id;

        const response = MockServer.env["pos.order"].sync_from_ui([order]);

        const partnerFields = MockServer.env["res.partner"]._load_pos_data_fields(configId);
        const partnerIds = response["pos.order"]
            .map((o) => o.partner_id)
            .flat()
            .filter((p) => !!p);
        return {
            "pos.order": response["pos.order"],
            "pos.order.line": response["pos.order.line"],
            "product.attribute.custom.value": response["product.attribute.custom.value"],
            "pos.payment": response["pos.payment"],
            "res.partner": MockServer.env["res.partner"].read(partnerIds, partnerFields, false),
        };
    };

    onRpc("/pos-self-order/process-order/kiosk", mockProcssOrder);
    onRpc("/pos-self-order/process-order/mobile", mockProcssOrder);
    onRpc("/pos-self-order/get-slots/", () => ({ usage_utc: {} }));
    onRpc("/pos-self-order/remove-order", () => ({}));
    onRpc("/pos-self-order/sync-from-ui", mockSyncOrder);
}

export const setupPoSEnvForSelfOrder = async () => {
    unpatchSelf();
    return await setupPosEnv();
};

export const setupSelfPosEnv = async (
    mode = "kiosk",
    service_mode = "counter",
    pay_after = "each"
) => {
    // Do not change these variables, they are in accordance with the setup data
    odoo.access_token = uuidv4();
    odoo.info = {
        isEnterprise: true,
    };
    patchWithCleanup(session, {
        db: "test",
        data: {
            config_id: 1,
        },
    });

    // Removing `pos` and its dependent services to avoid conflicts during `self_order` data loading.
    // Both `pos` and `self_order` rely on `pos_data`, but some models required by `self_order` (e.g., `res.users`)
    // are missing when `pos` is loaded. Hence, these services are excluded.
    const serviceNames = ["contextual_utils_service", "debug", "report", "pos"];
    serviceNames.forEach((serviceName) => registry.category("services").remove(serviceName));

    initMockRpc();
    await makeDialogMockEnv();
    const store = getService("self_order");

    store.config.self_ordering_mode = mode;
    store.config.self_ordering_service_mode = service_mode;
    store.config.self_ordering_pay_after = pay_after;

    await mountWithCleanup(selfOrderIndex);
    return store;
};

export const getFilledSelfOrder = async (store) => {
    const product1 = store.models["product.template"].get(5);
    const product2 = store.models["product.template"].get(6);

    await store.addToCart(product1, 3);
    await store.addToCart(product2, 2);

    store.currentOrder.access_token = uuidv4();
    return store.currentOrder;
};

export const addComboProduct = async (store) => {
    const models = store.models;
    const productCombo = models["product.template"].get(7);
    const comboItem1 = models["product.combo.item"].get(1);
    const comboItem3 = models["product.combo.item"].get(3);

    const comboValues = [
        {
            combo_item_id: comboItem1,
            configuration: {
                attribute_custom_values: {},
                attribute_value_ids: [],
                price_extra: 0,
            },
            qty: 1,
        },
        {
            combo_item_id: comboItem3,
            configuration: {
                attribute_custom_values: {},
                attribute_value_ids: [],
                price_extra: 0,
            },
            qty: 1,
        },
    ];
    await store.addToCart(productCombo, 2, "", {}, {}, comboValues);
    return store.currentOrder.lines.find((ol) => ol.combo_line_ids.length); // Parent Combo line
};

export async function checkKioskPreparationTicketData(store, expectedData) {
    const categoryIds = store.config.preparationCategories;
    const generator = store.ticketPrinter.getGenerator({
        models: store.models,
        order: store.currentOrder,
    });
    const changes = generator.generatePreparationData(categoryIds, {});
    if (!changes.length) {
        return "No preparation data generated";
    }
    const printedLines = changes[0].changes?.data || [];
    if (printedLines.length !== expectedData.length) {
        return `Mismatch in number of lines. Expected ${expectedData.length}, got ${printedLines.length}`;
    }
    for (const expected of expectedData) {
        const found = printedLines.find((line) => line.name === expected.name);
        if (!found) {
            return `Product ${expected.name} not found in preparation data`;
        }
        if (String(found.qty) !== String(expected.qty)) {
            return `Qty mismatch for ${expected.name}: expected ${expected.qty}, got ${found.qty}`;
        }
        if (expected.attributes) {
            for (const attr of expected.attributes) {
                const foundAttr = found.attributes?.find((a) => a.includes(attr));
                if (!foundAttr) {
                    return `Attribute ${attr} not found for ${expected.name}`;
                }
            }
        }
    }
    return true;
}
