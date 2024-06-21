import { roundDecimals } from "@web/core/utils/numbers";

export const computeComboItems = (
    parentProduct,
    childLineConf,
    pricelist,
    decimalPrecision,
    productTemplateAttributeValueById
) => {
    const comboItems = [];
    const parentLstPrice = parentProduct.get_price(pricelist, 1);
    const originalTotal = childLineConf.reduce((acc, conf) => {
        const originalPrice = conf.combo_item_id.combo_id.base_price;
        return acc + originalPrice;
    }, 0);

    let remainingTotal = parentLstPrice;
    for (const conf of childLineConf) {
        const comboItem = conf.combo_item_id;
        const combo = comboItem.combo_id;
        let priceUnit = roundDecimals(
            (combo.base_price * parentLstPrice) / originalTotal,
            decimalPrecision.find((dp) => dp.name === "Product Price").digits
        );
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
        comboItems.push({
            combo_item_id: comboItem,
            price_unit: totalPriceExtra,
            attribute_value_ids,
            attribute_custom_values: conf.configuration?.attribute_custom_values || {},
        });
    }

    return comboItems;
};
