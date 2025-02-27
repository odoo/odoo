export const computeComboItems = (
    parentProduct,
    childLineConf,
    pricelist,
    decimalPrecision,
    productTemplateAttributeValueById,
    childLineExtra = [],
    priceUnit = false
) => {
    const comboItems = [];
    childLineConf = computeComboItemsPrice(
        parentProduct,
        childLineConf,
        pricelist,
        decimalPrecision,
        productTemplateAttributeValueById,
        childLineExtra,
        priceUnit
    );

    for (const conf of childLineConf) {
        const attribute_value_ids = conf.configuration?.attribute_value_ids.map(
            (id) => productTemplateAttributeValueById[id]
        );
        comboItems.push({
            combo_item_id: conf.combo_item_id,
            price_unit: conf.price_unit,
            attribute_value_ids,
            attribute_custom_values: conf.configuration?.attribute_custom_values || {},
            qty: conf.qty,
            is_extra_combo_line: conf.is_extra_combo_line,
        });
    }

    return comboItems;
};

export const computeComboItemsPrice = (
    parentProduct,
    childLineConf,
    pricelist,
    decimalPrecision,
    productTemplateAttributeValueById,
    childLineExtra = [],
    priceUnit = false
) => {
    const parentLstPrice =
        priceUnit === false
            ? parentProduct.getPrice(pricelist, 1, 0, false, parentProduct)
            : priceUnit;
    const originalTotal = childLineConf.reduce((acc, conf) => {
        const originalPrice = conf.combo_item_id.combo_id.base_price * conf.qty;
        return acc + originalPrice;
    }, 0);

    const getAttributesPriceExtra = (attributeValueIds) =>
        (attributeValueIds ?? [])
            .map((attr) => attr?.price_extra || 0)
            .reduce((acc, price) => acc + price, 0);

    let remainingTotal = parentLstPrice;
    const ProductPrice = decimalPrecision.find((dp) => dp.name === "Product Price");
    for (const conf of childLineConf) {
        const comboItem = conf.combo_item_id;
        const combo = comboItem.combo_id;
        let priceUnit = ProductPrice.round((combo.base_price * parentLstPrice) / originalTotal);
        remainingTotal -= priceUnit * conf.qty;

        if (comboItem.id == childLineConf[childLineConf.length - 1].combo_item_id.id) {
            priceUnit += remainingTotal;
        }
        const attribute_value_ids = conf.configuration?.attribute_value_ids.map(
            (id) => productTemplateAttributeValueById[id]
        );

        const totalPriceExtra =
            priceUnit + getAttributesPriceExtra(attribute_value_ids) + comboItem.extra_price;
        conf.price_unit = totalPriceExtra;
    }

    // Process extra child lines using combo 'base_price'
    for (const extra of childLineExtra) {
        const comboItem = extra.combo_item_id;
        const priceUnit = ProductPrice.round(comboItem.combo_id.base_price);
        const attribute_value_ids = extra.configuration?.attribute_value_ids.map(
            (id) => productTemplateAttributeValueById[id]
        );

        const totalPriceExtra =
            priceUnit + getAttributesPriceExtra(attribute_value_ids) + comboItem.extra_price;
        extra.price_unit = totalPriceExtra;
        extra.is_extra_combo_line = true;
    }
    return [...childLineConf, ...childLineExtra];
};
