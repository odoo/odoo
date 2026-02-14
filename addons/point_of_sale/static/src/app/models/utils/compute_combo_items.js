export const computeComboItems = (
    parentProduct,
    childLineConf,
    pricelist,
    decimalPrecision,
    productTemplateAttributeValueById,
    childLineExtra = [],
    currency_id = false
) => {
    const comboItems = [];
    const parentLstPrice = parentProduct.getPrice(pricelist, 1, 0, false, parentProduct);
    let originalTotal = childLineConf.reduce((acc, conf) => {
        const originalPrice = conf.combo_item_id.combo_id.base_price * conf.qty;
        return acc + originalPrice;
    }, 0);

    const getAttributesPriceExtra = (attributeValueIds) =>
        (attributeValueIds ?? [])
            .map((attr) => attr?.price_extra || 0)
            .reduce((acc, price) => acc + price, 0);

    let remainingTotal = parentLstPrice;
    const ProductPrice = currency_id || decimalPrecision.find((dp) => dp.name === "Product Price");
    for (const conf of childLineConf) {
        const comboItem = conf.combo_item_id;
        const combo = comboItem.combo_id;
        let priceUnit = ProductPrice.round((combo.base_price * parentLstPrice) / originalTotal);
        remainingTotal -= priceUnit * conf.qty;

        if (comboItem.id == childLineConf[childLineConf.length - 1].combo_item_id.id) {
            priceUnit += remainingTotal;
            remainingTotal = 0;
        }
        const attribute_value_ids = conf.configuration?.attribute_value_ids?.map(
            (id) => productTemplateAttributeValueById[id]
        );

        const totalPriceExtra =
            priceUnit + getAttributesPriceExtra(attribute_value_ids) + comboItem.extra_price;
        comboItems.push({
            combo_item_id: comboItem,
            price_unit: totalPriceExtra,
            attribute_value_ids,
            attribute_custom_values: conf.configuration?.attribute_custom_values || {},
            qty: conf.qty,
        });
    }

    if (remainingTotal !== 0) {
        originalTotal = childLineExtra.reduce((acc, conf) => {
            const originalPrice = conf.combo_item_id.combo_id.base_price * conf.qty;
            return acc + originalPrice;
        }, 0);
    }

    // Process extra child lines using combo 'base_price'
    for (const extra of childLineExtra) {
        const comboItem = extra.combo_item_id;
        const combo = comboItem.combo_id;
        let priceUnit = ProductPrice.round(combo.base_price);
        if (remainingTotal !== 0) {
            const remaining = ProductPrice.round(
                (combo.base_price * parentLstPrice) / originalTotal
            );
            priceUnit += remaining;
            remainingTotal -= remaining * extra.qty;

            if (comboItem.id == childLineExtra[childLineExtra.length - 1].combo_item_id.id) {
                priceUnit += remainingTotal / extra.qty;
            }
        }
        const attribute_value_ids = extra.configuration?.attribute_value_ids.map(
            (id) => productTemplateAttributeValueById[id]
        );

        const totalPriceExtra =
            priceUnit + getAttributesPriceExtra(attribute_value_ids) + comboItem.extra_price;
        comboItems.push({
            combo_item_id: comboItem,
            price_unit: totalPriceExtra,
            attribute_value_ids,
            attribute_custom_values: extra.configuration?.attribute_custom_values || {},
            qty: extra.qty,
        });
    }

    return comboItems;
};
