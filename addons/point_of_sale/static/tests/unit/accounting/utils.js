const { DateTime } = luxon;

/**
 * We use a dedicated method for the price check because we don't want to use
 * getFilledOrder in case of modification of this method breaks the price test.
 *
 * This method is a copy of getFilledOrder from utils.js
 */
export const getFilledOrderForPriceCheck = async (store, data = {}) => {
    const order = store.addNewOrder(data);
    // This product1 has a 25% tax with a 100.0 price
    // This product2 has a 15% + 25% tax with a 1000.0 price
    const product1 = store.models["product.template"].get(15);
    const product2 = store.models["product.template"].get(16);

    const date = DateTime.now();
    order.write_date = date;
    order.create_date = date;
    order.pricelist_id = false;

    await store.addLineToOrder(
        {
            product_tmpl_id: product1,
            qty: 1,
            write_date: date,
            create_date: date,
        },
        order
    );
    await store.addLineToOrder(
        {
            product_tmpl_id: product2,
            qty: 1,
            write_date: date,
            create_date: date,
        },
        order
    );
    store.addPendingOrder([order.id]);
    return order;
};

export const prepareRoundingVals = (store, roundingAmount, roundingMethod, onlyCash = true) => {
    const config = store.config;
    const product1 = store.models["product.template"].get(15);
    const product2 = store.models["product.template"].get(16);
    const cashPm = store.models["pos.payment.method"].find((pm) => pm.is_cash_count);
    const cardPm = store.models["pos.payment.method"].find((pm) => !pm.is_cash_count);

    // Changes prices to have a non rounded change
    product1.list_price = 15.73;
    product2.list_price = 23.49;
    product1.product_variant_ids[0].lst_price = 15.73;
    product2.product_variant_ids[0].lst_price = 23.49;

    config.cash_rounding = true;
    config.only_round_cash_method = onlyCash;
    config.rounding_method = store.models["account.cash.rounding"].create({
        name: "roudning",
        rounding: roundingAmount,
        rounding_method: roundingMethod,
        strategy: "add_invoice_line",
    });

    return { config, cashPm, cardPm };
};
