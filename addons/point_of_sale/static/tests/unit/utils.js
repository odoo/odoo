import { uuidv4 } from "@point_of_sale/utils";
import { getService, makeDialogMockEnv, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { tick, waitUntil } from "@odoo/hoot-dom";
import { Deferred } from "@odoo/hoot-mock";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

const { DateTime } = luxon;

export const setupPosEnv = async () => {
    // Do not change these variables, they are in accordance with the demo data
    odoo.pos_session_id = 1;
    odoo.pos_config_id = 1;
    odoo.login_number = 1;
    odoo.from_backend = 0;
    odoo.access_token = uuidv4(); // Avoid indexedDB conflicts
    odoo.info = {
        db: `pos-${uuidv4()}`, // Avoid indexedDB conflicts
        isEnterprise: true,
    };

    await makeDialogMockEnv();
    const store = getService("pos");
    store.setCashier(store.user);
    return store;
};

export const getFilledOrder = async (store) => {
    const order = store.addNewOrder();
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

export async function waitUntilOrdersSynced(store, options) {
    await waitUntil(() => !store.syncingOrders.size, options);
    await tick();
}

export const mountPosDialog = async (component, props) => {
    patchDialogComponent(component);
    const dialog = getService("dialog");
    const root = await mountWithCleanup(MainComponentsContainer);
    const deferred = new Deferred();

    const getComponentInstance = (root) => {
        const flattenedChildren = (comp, acc = {}) => {
            const array = Object.values(comp.children);
            for (const child of array) {
                acc[child.name] = child;
                flattenedChildren(child, acc);
            }
            return acc;
        };
        const components = flattenedChildren(root);
        return components[component.name];
    };

    dialog.add(component, {
        ...props,
        onMounted() {
            const dialogComponent = getComponentInstance(root.__owl__);
            deferred.resolve(dialogComponent.component);
        },
    });
    return await deferred;
};

export const patchDialogComponent = (component) => {
    component.props = [...component.props, "onMounted?"];
    patch(component.prototype, {
        setup() {
            super.setup();

            onMounted(() => {
                this.props.onMounted && this.props.onMounted();
            });
        },
    });
};
