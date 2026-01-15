import configuratorTourUtils from '@sale/js/tours/product_configurator_tour_utils';

function assertProductOutOfStock(productName) {
    return [
        {
            content: `Assert that ${productName} is out of stock`,
            trigger: `
                ${configuratorTourUtils.productSelector(productName)}
                td.o_sale_product_configurator_qty:contains("Out of stock")
            `,
        },
        {
            content: `Assert that ${productName} has no quantity`,
            trigger: `
                ${configuratorTourUtils.productSelector(productName)}
                td.o_sale_product_configurator_qty:not(:has(input[name="sale_quantity"]))
            `,
        },
    ];
}

function assertOptionalProductOutOfStock(productName) {
    return [
        {
            content: `Assert that ${productName} is out of stock`,
            trigger: `
                ${configuratorTourUtils.optionalProductSelector(productName)}
                td.o_sale_product_configurator_price:contains("Out of stock")
            `,
        },
        {
            content: `Assert that ${productName} has no "Add" button`,
            trigger: `
                ${configuratorTourUtils.optionalProductSelector(productName)}
                td.o_sale_product_configurator_price:not(:has(button:contains("Add")))
            `,
        },
    ];
}

export default {
    assertProductOutOfStock,
    assertOptionalProductOutOfStock,
};
