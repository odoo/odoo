import { uuidv4 } from "@point_of_sale/utils";
import {
    getService,
    makeDialogMockEnv,
    mountWithCleanup,
    patchWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { animationFrame, tick, waitFor, waitUntil } from "@odoo/hoot-dom";
import { expect } from "@odoo/hoot";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { user } from "@web/core/user";

const { DateTime } = luxon;

export const setupPosEnv = async () => {
    // Do not change these variables, they are in accordance with the demo data
    odoo.pos_session_id = 1;
    odoo.pos_config_id = 1;
    odoo.from_backend = 0;
    odoo.access_token = uuidv4(); // Avoid indexedDB conflicts
    odoo.info = {
        db: `pos-${uuidv4()}`, // Avoid indexedDB conflicts
        isEnterprise: true,
    };

    await makeDialogMockEnv();
    onRpc("/css", () => "");
    const store = getService("pos");
    store.setCashier(store.user);
    patchWithCleanup(user, {
        // Needed for the allowProductCreation method
        // and for product reorder in the frontend
        checkAccessRight: (model, operation) =>
            (operation === "create" && model === "product.product") ||
            (operation === "write" && model === "product.template"),
    });
    return store;
};

export const getFilledOrder = async (store, data = {}) => {
    const order = store.addNewOrder(data);
    const product1 = store.models["product.template"].get(5);
    const product2 = store.models["product.template"].get(6);
    const date = DateTime.now();
    order.write_date = date;
    order.create_date = date;

    await store.addLineToOrder(
        {
            product_tmpl_id: product1,
            qty: 3,
            write_date: date,
            create_date: date,
        },
        order
    );
    await store.addLineToOrder(
        {
            product_tmpl_id: product2,
            qty: 2,
            write_date: date,
            create_date: date,
        },
        order
    );
    store.addPendingOrder([order.id]);
    return order;
};

export const makeOrder = (store, overrides = {}) => {
    const order = store.createNewOrder();
    Object.assign(order, {
        state: "draft",
        date_order: DateTime.now(),
        pos_reference: "Order 00001",
        getScreenData: () => ({ name: "ProductScreen" }),
        ...overrides,
    });
    return order;
};

export async function waitUntilOrdersSynced(store, options) {
    await waitUntil(() => !store.syncingOrders.size, options);
    await tick();
}

export const mountPosDialog = async (component, props) => {
    const dialog = getService("dialog");
    const root = await mountWithCleanup(MainComponentsContainer);
    const getComponentInstance = (root) => {
        const flattenedChildren = (comp, acc = {}) => {
            for (const child of Object.values(comp.children)) {
                acc[child.componentName] = child;
                flattenedChildren(child, acc);
            }
            return acc;
        };
        const components = flattenedChildren(root);
        return components[component.name];
    };
    dialog.add(component, props);

    const dialogNode = await waitUntil(() => getComponentInstance(root.__owl__));
    return dialogNode.component;
};

export const expectFormattedPrice = (value, expected) => {
    expect(value).toBe(expected.replaceAll(" ", "\u00a0"));
};

export const dialogActions = async (action, steps = []) => {
    // Launch the action in a promise to be able to await the end of the steps
    await mountWithCleanup(MainComponentsContainer);
    const promise = new Promise((resolve) => {
        const call = async (fn) => {
            const result = await fn();
            resolve(result);
        };
        call(action);
    });

    // Wait for the dialog to be mounted
    await waitFor(".o_dialog");

    // Execute the steps one by one
    for (const step of steps) {
        await step();
        await animationFrame();
    }

    // Return the result of the action
    return await promise;
};

export const createPaymentLine = (store, order, paymentMethod, data = {}) =>
    store.models["pos.payment"].create({
        amount: 10,
        payment_method_id: paymentMethod.id,
        pos_order_id: order.id,
        write_date: DateTime.now(),
        create_date: DateTime.now(),
        ...data,
    });

export const activateMountingDialogs = async (env) => {
    await mountWithCleanup(MainComponentsContainer, { env });
};

export const normalizeFunctionsInObject = (obj) =>
    Object.fromEntries(
        Object.entries(obj).map(([key, value]) => [
            key,
            typeof value === "function" ? "function" : value,
        ])
    );
