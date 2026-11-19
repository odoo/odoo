import { expect, test, tick } from "@odoo/hoot";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { getFilledOrder, setupPosEnv, setupPreparationPrinting } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

const byProduct = (a, b) => a.product_id - b.product_id;

const linesToPrint = (order) =>
    order.lines
        .map((line) => ({ product_id: line.product_id.id, quantity: line.qty }))
        .sort(byProduct);

const recordOrderSyncs = (store) => {
    const syncs = [];
    const call = store.data.call.bind(store.data);
    store.data.call = async (model, method, ...args) => {
        if (model === "pos.order" && method === "sync_from_ui") {
            syncs.push(args);
        }
        return call(model, method, ...args);
    };
    return syncs;
};

test("validateOrder", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const product_tmpl_id = store.models["product.template"].get(8);
    await store.addLineToOrder({ product_tmpl_id, qty: 0 }, order);

    const fastPaymentMethod = order.config.fast_payment_method_ids[0];
    const validation = new OrderPaymentValidation({
        pos: store,
        orderUuid: store.getOrder().uuid,
        fastPaymentMethod: fastPaymentMethod,
    });
    await validation.validateOrder(false);
    // validateOrder launches a promise. We need to wait for its resolution.
    // tick will ensure that all microtasks like resolved promises are handled.
    // Here the promise is resolved as it is only synchronous code.
    await tick();
    expect(order.payment_ids[0].payment_method_id).toEqual(fastPaymentMethod);
    expect(order.state).toBe("paid");
    expect(order.amount_paid).toBe(595);
    expect(order.lines.length).toBe(3); // Keep lines with zero quantity
});
test("isOrderValid", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    order.setToInvoice(true);
    const validation = new OrderPaymentValidation({
        pos: store,
        orderUuid: store.getOrder().uuid,
    });
    const isOrderValid = await validation.isOrderValid(false);
    expect(order.lines).toHaveLength(0);
    expect(isOrderValid).toBe(false); // The order cannot be invoiced if the order line count is zero.
});
test("finalizeValidation prints the unsent changes and syncs the order once", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    order.addPaymentline(store.models["pos.payment.method"].find((pm) => pm.type === "bank"));
    const expectedLines = linesToPrint(order);
    const printedLines = setupPreparationPrinting(store);
    const syncs = recordOrderSyncs(store);

    const validation = new OrderPaymentValidation({ pos: store, orderUuid: order.uuid });
    await validation.finalizeValidation();

    expect(order.state).toBe("paid");
    expect(syncs).toHaveLength(1);
    expect(printedLines.sort(byProduct)).toEqual(expectedLines);
    expect(order.isDirty()).toBe(false);
});
test("afterOrderValidation prints the unsent changes of an order saved as paid without syncing it", async () => {
    // e.g. online payments, where the server marks the order as paid
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    order.addPaymentline(store.models["pos.payment.method"].find((pm) => pm.type === "bank"));
    order.state = "paid";
    await store.syncAllOrders({ orders: [order] });
    const expectedLines = linesToPrint(order);
    const printedLines = setupPreparationPrinting(store);
    const syncs = recordOrderSyncs(store);

    const validation = new OrderPaymentValidation({ pos: store, orderUuid: order.uuid });
    await validation.afterOrderValidation(true);

    expect(syncs).toHaveLength(0);
    expect(printedLines.sort(byProduct)).toEqual(expectedLines);
    expect(order.isDirty()).toBe(false);
});
