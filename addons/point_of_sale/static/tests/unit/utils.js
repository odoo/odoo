import { uuidv4 } from "@point_of_sale/utils";
import { getService, makeDialogMockEnv } from "@web/../tests/web_test_helpers";
import { tick, waitUntil } from "@odoo/hoot-dom";

const { DateTime } = luxon;

export const setupPosEnv = async () => {
    // Do not change these variables, they are in accordance with the demo data
    odoo.pos_session_id = 1;
    odoo.pos_config_id = 1;
    odoo.login_number = 1;
    odoo.from_backend = 0;
    odoo.access_token = uuidv4(); // Avoid indexedDB conflicts
    odoo.info = {
        db: "pos",
        isEnterprise: true,
        server_version: "1.0",
    };

    await makeDialogMockEnv();
    const store = getService("pos");
    store.setCashier(store.user);
    return store;
};

export const getFilledOrder = async (store, paid = false, refund = false) => {
    const order = store.addNewOrder();
    const product1 = store.models["product.template"].get(5);
    const product2 = store.models["product.template"].get(6);
    let refund1 = false;
    let refund2 = false;

    if (refund) {
        order.is_refund = true;
        const refundOrder = store.models["pos.order"].create({
            id: `refund_${order.id}`,
            name: `Refund of ${order.name}`,
            pos_session_id: store.session,
            pos_config_id: store.config,
            amount_paid: 185,
            amount_total: 185,
            state: "paid",
        });
        refund1 = store.models["pos.order.line"].create({
            product_id: product1.product_variant_ids[0],
            price_unit: product1.list_price,
            order_id: refundOrder,
            qty: 3,
        });
        refund2 = store.models["pos.order.line"].create({
            product_id: product2.product_variant_ids[0],
            price_unit: product2.list_price,
            order_id: refundOrder,
            qty: 2,
        });
        refundOrder.recomputeOrderData();
    }
    const date = DateTime.now();
    order.write_date = date;
    order.create_date = date;

    await store.addLineToOrder(
        {
            product_tmpl_id: product1,
            qty: refund ? -3 : 3,
            write_date: date,
            create_date: date,
            refunded_orderline_id: refund1,
        },
        order
    );
    await store.addLineToOrder(
        {
            product_tmpl_id: product2,
            qty: refund ? -2 : 2,
            refunded_orderline_id: refund2,
            write_date: date,
            create_date: date,
        },
        order
    );

    if (paid) {
        order.recomputeOrderData();
        const amountTotal = order.getTotalWithTax();
        order.state = "paid";

        store.models["pos.payment"].create({
            amount: amountTotal,
            pos_order_id: order,
            payment_method_id: store.models["pos.payment.method"].find((m) => m.name === "Cash"),
        });
    }

    order.recomputeOrderData();
    store.addPendingOrder([order.id]);
    return order;
};

export async function waitUntilOrdersSynced(store, options) {
    await waitUntil(() => !store.syncingOrders.size, options);
    await tick();
}
