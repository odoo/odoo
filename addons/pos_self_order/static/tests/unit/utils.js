import { uuidv4 } from "@point_of_sale/utils";
import {
    getService,
    makeMockEnv,
    onRpc,
    patchWithCleanup,
    MockServer,
} from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { registry } from "@web/core/registry";
import { mockSelfRoutes } from "./router_data.js";

export function patchSession() {
    // Do not change these variables, they are in accordance with the setup data
    patchWithCleanup(session, {
        data: {
            config_id: 1,
            self_ordering_mode: "kiosk",
        },
        db: "test",
    });
}

export function initMockRpc() {
    onRpc("/pos-self/relations/1", () =>
        MockServer.env["pos.session"].load_data_params({ self_ordering: true })
    );
    onRpc("/pos-self/data/1", () =>
        MockServer.env["pos.session"].load_data({ self_ordering: true })
    );
    onRpc("/pos-self-order/process-order/kiosk", async (request) => {
        const { params } = await request.json();
        const response = MockServer.env["pos.order"].sync_from_ui([params.order]);
        const models = MockServer.env["pos.session"]._load_self_data_models();
        return Object.fromEntries(Object.entries(response).filter(([key]) => models.includes(key)));
    });
}

export const setupSelfPosEnv = async () => {
    odoo.access_token = uuidv4();
    odoo.info = {
        isEnterprise: true,
    };

    // Removing `pos` and its dependent services to avoid conflicts during `self_order` data loading.
    // Both `pos` and `self_order` rely on `pos_data`, but some models required by `self_order` (e.g., `res.users`)
    // are missing when `pos` is loaded. Hence, these services are excluded.
    const serviceNames = ["contextual_utils_service", "debug", "report", "pos"];
    serviceNames.forEach((serviceName) => registry.category("services").remove(serviceName));

    initMockRpc();
    await makeMockEnv();
    const store = getService("self_order");

    // Ensure mock routes are registered for the self order router service.
    // This prevents navigation errors during test execution when route-dependent methods are called.
    const router = getService("router");
    router.registerRoutes(mockSelfRoutes);

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
