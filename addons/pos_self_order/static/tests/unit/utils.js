import { uuidv4 } from "@point_of_sale/utils";
import {
    getService,
    makeMockEnv,
    onRpc,
    patchWithCleanup,
    MockServer,
    mountWithCleanup,
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

    const mockProcssOrder = async (request) => {
        const { params } = await request.json();
        const response = MockServer.env["pos.order"].sync_from_ui([params.order]);
        const models = MockServer.env["pos.session"]._load_self_data_models();
        return Object.fromEntries(Object.entries(response).filter(([key]) => models.includes(key)));
    };

    onRpc("/pos-self-order/process-order/kiosk", mockProcssOrder);
    onRpc("/pos-self-order/process-order/mobile", mockProcssOrder);
    onRpc("/pos-self-order/get-slots/", () => ({ usage_utc: {} }));
    onRpc("/pos-self-order/remove-order", () => ({}));
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
    await makeMockEnv();
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
    store.addToCart(productCombo, 2, "", {}, {}, comboValues);
    return store.currentOrder.lines.find((ol) => ol.combo_line_ids.length); // Parent Combo line
};
