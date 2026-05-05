const { DateTime } = luxon;

/**
 * Utility to create a new order with loyalty flow.
 *
 * @param {Object} store
 * @param {Array} products
 * @param {Array} rewardLines
 * @param {Object|null} partner
 * @returns {Object} order
 */
export async function createOrderWithLoyalty(
    store,
    products = [],
    partner = null,
    rewardLines = []
) {
    store.addNewOrder();
    const order = store.getOrder();

    if (partner) {
        order.setPartner(partner);
    }

    const date = DateTime.now();
    order.write_date = date;
    order.create_date = date;

    // Add normal products through store flow
    for (const p of products) {
        const product = p.product;

        await store.addLineToCurrentOrder(
            {
                product_id: product,
                product_tmpl_id: product.product_tmpl_id,
                qty: p.qty || 1,
            },
            {
                price_unit: p.price,
            }
        );
    }

    // Add reward lines manually
    for (const line of rewardLines) {
        order.addOrderline(
            await store.models["pos.order.line"].create({
                product_id: line.product_id,
                qty: line.qty || 1,
                price_unit: line.price_unit || 0,
                is_reward_line: line.is_reward_line || false,
                reward_id: line.reward_id || null,
                price_type: line.price_type || "automatic",
                order_id: order,
            })
        );
    }

    return order;
}

export async function getFilledOrderLoyalty(store) {
    return await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 3, price: 100 },
        { product: store.models["product.product"].get(6), qty: 2, price: 100 },
    ]);
}
