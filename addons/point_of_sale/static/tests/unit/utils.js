import { uuidv4 } from "@point_of_sale/utils";
import { getService, makeMockEnv } from "@web/../tests/web_test_helpers";

export const setupPosEnv = async () => {
    // Do not change these variables, they are in accordance with the
    // point_of_sale/static/tests/unit/data/base_data.js file.
    odoo.pos_session_id = 1;
    odoo.pos_config_id = 1;
    odoo.login_number = 1;
    odoo.from_backend = 0;
    odoo.access_token = uuidv4(); // Avoid indexedDB conflicts
    odoo.info = {
        db: "pos",
        isEnterprise: true,
    };

    await makeMockEnv();
    const store = getService("pos");
    store.setCashier(store.user);
    return store;
};

export const getFilledOrder = async (store) => {
    const order = store.addNewOrder();
    const product1 = store.models["product.template"].get(5);
    const product2 = store.models["product.template"].get(6);

    await store.addLineToOrder(
        {
            product_tmpl_id: product1,
            qty: 3,
        },
        order
    );
    await store.addLineToOrder(
        {
            product_tmpl_id: product2,
            qty: 2,
        },
        order
    );
    return order;
};
