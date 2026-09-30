import configuratorTourUtils from '@sale/js/tours/product_configurator_tour_utils';

function assertProductStrikethroughPrice(productName, price) {
    return {
        content: `Assert that ${productName} was reduced from ${price}`,
        trigger: `
            ${configuratorTourUtils.productSelector(productName)}
            .oe_striked_price:contains("${price}")
        `,
    };
}

function assertOptionalProductStrikethroughPrice(productName, price) {
    return {
        content: `Assert that ${productName} was reduced from ${price}`,
        trigger: `
            ${configuratorTourUtils.optionalProductSelector(productName)}
            .oe_striked_price:contains("${price}")
        `,
    };
}

function assertProductZeroPriced(productName) {
    return [
        {
            content: `Assert that ${productName} is not available for sale`,
            trigger: `
                ${configuratorTourUtils.productSelector(productName)}
                td.o_sale_product_configurator_qty:contains("Not available for sale")
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

function assertOptionalProductZeroPriced(productName) {
    return [
        {
            content: `Assert that ${productName} is not available for sale`,
            trigger: `
                ${configuratorTourUtils.optionalProductSelector(productName)}
                td.o_sale_product_configurator_price:contains("Not available for sale")
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
    assertProductStrikethroughPrice,
    assertOptionalProductStrikethroughPrice,
    assertProductZeroPriced,
    assertOptionalProductZeroPriced,
};
