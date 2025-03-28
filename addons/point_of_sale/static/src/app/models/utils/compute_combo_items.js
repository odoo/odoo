export const computeComboItems = (
    parentProduct,
    childLineConf,
    pricelist,
    decimalPrecision,
    productTemplateAttributeValueById,
    priceUnit = false
) => {
    const comboItems = [];
    childLineConf = computeComboItemsPrice(
        parentProduct,
        childLineConf,
        pricelist,
        decimalPrecision,
        productTemplateAttributeValueById,
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
    priceUnit = false
) => {
    const parentLstPrice =
        priceUnit === false
            ? parentProduct.getPrice(pricelist, 1, 0, false, parentProduct)
            : priceUnit;
    const originalTotal = childLineConf.reduce((acc, conf) => {
        const originalPrice = conf.combo_item_id.combo_id.base_price;
        return acc + originalPrice;
    }, 0);

    let remainingTotal = parentLstPrice;
    const ProductPrice = decimalPrecision.find((dp) => dp.name === "Product Price");
    for (const conf of childLineConf) {
        const comboItem = conf.combo_item_id;
        const combo = comboItem.combo_id;
        let priceUnit = ProductPrice.round((combo.base_price * parentLstPrice) / originalTotal);
        remainingTotal -= priceUnit;
        if (comboItem.id == childLineConf[childLineConf.length - 1].combo_item_id.id) {
            priceUnit += remainingTotal;
        }
        const attribute_value_ids = conf.configuration?.attribute_value_ids.map(
            (id) => productTemplateAttributeValueById[id]
        );
        const attributesPriceExtra = (attribute_value_ids ?? [])
            .map((attr) => attr?.price_extra || 0)
            .reduce((acc, price) => acc + price, 0);
        const totalPriceExtra = priceUnit + attributesPriceExtra + comboItem.extra_price;
        conf.price_unit = totalPriceExtra;
    }
    return childLineConf;
};
