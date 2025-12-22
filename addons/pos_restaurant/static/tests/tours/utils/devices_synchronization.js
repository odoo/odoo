/* global posmodel */

const getData = ({ lineProductName, productName, partnerName } = {}) => {
    const order = posmodel.models["pos.order"].find((o) => o.pos_reference === "device_sync");

    let partner = null;
    if (partnerName) {
        partner = posmodel.models["res.partner"].find((p) => p.name === partnerName);
    }

    let line = null;
    if (lineProductName) {
        line = order.lines.find((l) => l.product_id.display_name === lineProductName);
    }

    let product = null;
    if (productName) {
        product = posmodel.models["product.product"].find((p) => p.display_name === productName);
    }

    return { order, line, product, partner };
};

const notify = async (orderIds = []) => {
    const recordIds = {};
    if (orderIds.lenght) {
        recordIds["pos.order"] = orderIds;
    }
    const orm = posmodel.env.services.orm;
    await orm.call("pos.config", "notify_synchronisation", [
        posmodel.config.id,
        posmodel.session.id,
        999,
        recordIds,
    ]);
};

const getLineData = (product, order, quantity) => ({
    name: product.display_name,
    order_id: order.id,
    product_id: product.id,
    price_unit: product.lst_price,
    price_subtotal: product.lst_price * quantity,
    price_subtotal_incl: product.lst_price * quantity,
    discount: 0,
    qty: quantity,
});

// In the point-of-sale code, we consider that synchronization is necessary
// when the write_date of the local order is smaller than that of the server.
// To prevent the PoS from ignoring our synchronization.
const writeOnOrder = async (order, data) => {
    const sec = new Date(order.write_date).getMilliseconds() + 1010;
    const timeout = Math.ceil(sec - new Date().getMilliseconds(), 0);
    await new Promise((res) => setTimeout(res, timeout));
    const orm = posmodel.env.services.orm;
    await orm.write("pos.order", [order.id], data);
    await notify([order.id]);
};

export function markOrderAsPaid() {
    return [
        {
            trigger: "body",
            run: async () => {
                const { order } = getData({});
                await writeOnOrder(order, {
                    state: "paid",
                    amount_paid: order.amount_total,
                    amount_return: 0,
                    amount_tax: 0,
                    amount_total: 0,
                });
            },
        },
    ];
}

export function createNewOrderOnTable(tableName, productTuple) {
    return [
        {
            trigger: "body",
            run: async () => {
                const orm = posmodel.env.services.orm;
                const prices = {
                    amount_paid: 0,
                    amount_return: 0,
                    amount_tax: 0,
                    amount_total: 0,
                };
                const lines = productTuple.map(([productName, quantity]) => {
                    const product = posmodel.models["product.product"].find(
                        (p) => p.display_name === productName
                    );
                    const lineData = getLineData(product, false, quantity);
                    prices.amount_paid += lineData.price_subtotal;
                    prices.amount_return += lineData.price_subtotal;
                    return [
                        0,
                        0,
                        {
                            ...lineData,
                            price_subtotal: lineData.price_subtotal,
                            price_subtotal_incl: lineData.price_subtotal_incl,
                        },
                    ];
                });
                const table = posmodel.models["restaurant.table"].find(
                    (t) => t.table_number === parseInt(tableName)
                );
                const [orderId] = await orm.create("pos.order", [
                    {
                        ...prices,
                        pos_reference: `device_sync`,
                        config_id: posmodel.config.id,
                        session_id: posmodel.session.id,
                        table_id: table.id,
                        lines,
                    },
                ]);
                await notify([orderId]);
            },
        },
    ];
}
