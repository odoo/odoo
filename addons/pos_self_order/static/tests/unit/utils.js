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
import { SelfOrderRouter } from "@pos_self_order/app/services/self_order_router_service";
import { PosSession } from "@point_of_sale/../tests/unit/data/pos_session.data";

function checkPosOrder(deviceType, order) {
    const count = MockServer.env["pos.order"].search_count([]) + 1;
    const configId = order.config_id || 1;
    const pos_reference = `0001-001-${String(count).padStart(5, "0")}`;
    const prefix = deviceType === "kiosk" ? `K${configId}-` : "S";
    const tracking_number = `${prefix}${count}`;

    if (!order.access_token) {
        order.access_token = uuidv4();
    }

    let floating_order_name = order.floating_order_name;
    if (deviceType === "kiosk") {
        floating_order_name = order.table_stand_number
            ? `Table tracker ${order.table_stand_number}`
            : String(count);
    } else if (!floating_order_name) {
        floating_order_name = order.table_id
            ? `Self-Order T ${order.table_id}`
            : `Self-Order ${count}`;
    }

    order.pos_reference = pos_reference;
    order.tracking_number = tracking_number;
    order.floating_order_name = floating_order_name;
    order.state = order.state || "draft";
    order.source = deviceType === "kiosk" ? "kiosk" : "mobile";
    return order;
}

export function initMockRpc() {
    onRpc("/pos-self/relations/1", () =>
        MockServer.env["pos.session"].load_data_params({ self_ordering: true })
    );
    onRpc("/pos-self/data/1", () =>
        MockServer.env["pos.session"].load_data({ self_ordering: true })
    );

    const mockProcssOrder = async (request) => {
        const { params } = await request.json();
        const deviceType = request.url.includes("/kiosk") ? "kiosk" : "mobile";
        if (params.order.amount_total == 0) {
            params.order.state = "paid";
        }
        checkPosOrder(deviceType, params.order);
        const response = MockServer.env["pos.order"].sync_from_ui([params.order]);
        const models = MockServer.env["pos.session"]._load_self_data_models();
        return Object.fromEntries(Object.entries(response).filter(([key]) => models.includes(key)));
    };

    onRpc("/pos-self-order/process-order/kiosk", mockProcssOrder);
    onRpc("/pos-self-order/process-order/mobile", mockProcssOrder);
    onRpc("/pos-self-order/remove-order", () => ({}));
    onRpc("/pos-self-order/change-printer-status", () => ({}));
}

export const setupPoSEnvForSelfOrder = async () => {
    unpatchSelf();
    return await setupPosEnv();
};

export const setupSelfPosEnv = async (
    mode = "kiosk",
    service_mode = "counter",
    pay_after = "each",
    configOverrides = {},
    sessionOpened = false
) => {
    // Do not change these variables, they are in accordance with the setup data
    odoo.pos_config_id = 1;
    odoo.self_ordering_mode = mode;
    odoo.access_token = uuidv4();
    odoo.info = {
        isEnterprise: true,
    };

    if (sessionOpened) {
        odoo.pos_session_id = 1;
        PosSession._records = PosSession._records.map((r) => ({
            ...r,
            state: "opened",
        }));
    } else {
        odoo.pos_session_id = null;
    }

    patchWithCleanup(session, {
        db: "test",
        test_mode: true,
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

    if (Object.keys(configOverrides).length) {
        Object.assign(store.config, configOverrides);
        store.initProducts();
        store.computeAvailableCategories();
    }

    await mountWithCleanup(selfOrderIndex);
    return store;
};

export const mockRouterNavigate = () => {
    patchWithCleanup(SelfOrderRouter.prototype, {
        navigate(routeName, routeParams = {}, historyState = {}) {
            const { route } = this.registeredRoutes[routeName];
            const pathName = route.replace(
                /\{\w+:(\w+)\}/g,
                (match, paramName) => routeParams[paramName]
            );
            this.path = pathName;
            this.historyPage = pathName;
            window.history.replaceState(historyState, "");
        },
    });
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

export function mockNavigate(router) {
    const navigate = [];
    router.navigate = (route) => navigate.push(route);
    return navigate;
}
