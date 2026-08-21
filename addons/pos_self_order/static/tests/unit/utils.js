import { uuidv4 } from "@point_of_sale/utils";
import {
    assignDialogTestEnv,
    getService,
    onRpc,
    patchWithCleanup,
    MockServer,
    mountWithCleanup,
    makeTestApp,
} from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { registry } from "@web/core/registry";
import { selfOrderIndex } from "@pos_self_order/app/self_order_index";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { unpatchSelf } from "@pos_self_order/app/plugins/pos_data_plugin";
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
    onRpc("/pos-self/data/1", () => MockServer.env["pos.config"].load_self_data());

    const mockProcssOrder = async (request) => {
        const { params } = await request.json();
        const deviceType = request.url.includes("/kiosk") ? "kiosk" : "mobile";
        if (params.order.amount_total == 0) {
            params.order.state = "paid";
        }
        checkPosOrder(deviceType, params.order);
        const response = MockServer.env["pos.order"].sync_from_ui([params.order]);
        const models = MockServer.env["pos.config"]._load_self_data_models();
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

    const mockValidatePartner = async (request) => {
        const { params } = await request.json();
        delete params.access_token;
        delete params.preset_id;
        const partnerId = MockServer.env["res.partner"].create(params);
        const partnerFields = MockServer.env["res.partner"]._load_pos_data_fields(odoo.config_id);
        return {
            "res.partner": MockServer.env["res.partner"].read([partnerId], partnerFields, false),
        };
    };

    const mockGetUserData = async (request) => {
        const { params } = await request.json();
        const order_access_tokens = params.order_access_tokens || [];
        const orderIds = [];
        for (const token of order_access_tokens) {
            const orders = MockServer.env["pos.order"].search_read([
                ["access_token", "=", token.access_token],
            ]);
            for (const order of orders) {
                if (order.state !== token.state || order.write_date > token.write_date) {
                    orderIds.push(order.id);
                }
            }
        }
        return orderIds.length > 0 ? MockServer.env["pos.order"].read_pos_data(orderIds) : {};
    };

    const mockGetSlots = async (request) => {
        const { params } = await request.json();
        const usage_utc = {};
        const orders = MockServer.env["pos.order"].search_read([
            ["preset_id", "=", params.preset_id],
            ["preset_time", "!=", false],
            ["state", "in", ["draft", "paid"]],
        ]);
        for (const order of orders) {
            usage_utc[order.preset_time] ??= [];
            usage_utc[order.preset_time].push(order.id);
        }
        return { usage_utc };
    };

    onRpc("/pos-self-order/process-order/kiosk", mockProcssOrder);
    onRpc("/pos-self-order/process-order/mobile", mockProcssOrder);
    onRpc("/pos-self-order/get-slots", mockGetSlots);
    onRpc("/pos-self-order/remove-order", () => ({}));
    onRpc("/pos-self-order/sync-from-ui", mockSyncOrder);
    onRpc("/pos-self-order/validate-partner", mockValidatePartner);
    onRpc("/pos-self-order/change-printer-status", () => ({}));
    onRpc("/pos-self-order/get-user-data", mockGetUserData);
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

    // Removing `pos` and its dependent services to avoid conflicts during `self_order` data loading.
    // Both `pos` and `self_order` rely on `pos_data`, but some models required by `self_order` (e.g., `res.users`)
    // are missing when `pos` is loaded. Hence, these services are excluded.
    const serviceNames = ["contextual_utils_service", "debug", "report", "pos"];
    serviceNames.forEach((serviceName) => registry.category("services").remove(serviceName));

    initMockRpc();
    assignDialogTestEnv();
    await makeTestApp();
    const store = getService("self_order");

    store.config.self_ordering_mode = mode;
    store.config.self_ordering_service_mode = service_mode;
    store.config.self_ordering_pay_after = pay_after;
    patchWithCleanup(store.ticketPrinter, {
        async generateIframe(template, data) {
            return document.createElement("iframe");
        },
        setIframeSizeFromPrinter(iframe, printer) {
            return;
        },
        async generateImage() {
            return "fake_image_data";
        },
    });

    if (Object.keys(configOverrides).length) {
        Object.assign(store.config, configOverrides);
        store.initProducts();
        store.computeAvailableCategories();
    }

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

export function mockLNAPermissionCheck() {
    let called = false;
    patchWithCleanup(navigator.permissions, {
        async query() {
            called = true;
            return { state: "granted", onchange: null };
        },
    });

    return {
        get wasCalled() {
            return called;
        },
        reset() {
            called = false;
        },
    };
}

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
        const found = printedLines.find((line) => line.basic_name === expected.name);
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

export function mockNavigate(router) {
    const navigate = [];

    patchWithCleanup(router, {
        navigate(route) {
            navigate.push(route);
        },
    });

    return navigate;
}
