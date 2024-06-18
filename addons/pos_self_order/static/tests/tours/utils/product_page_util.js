export function clickProduct(productName) {
    return {
        content: `Click on product '${productName}'`,
        trigger: `.self_order_product_card span:contains('${productName}')`,
        run: "click",
    };
}

export function clickCancel() {
    return [
        {
            content: `Click on Cancel button`,
            trigger: `.btn.btn-cancel`,
            run: "click",
        },
        {
            content: `Click on button Cancel Order`,
            trigger: `.btn.btn-lg:contains('Cancel Order')`,
            run: "click",
        },
    ];
}

export function clickDiscard() {
    return {
        content: "Click on Discard button",
        trigger: ".btn.btn-secondary .oi-chevron-left",
        run: "click",
    };
}

export function setupAttribute(attributes, addToCart = true) {
    const steps = [];
    if (addToCart) {
        steps.push({
            content: `Click on 'Add to cart' button`,
            trigger: `.btn.btn-primary`,
            run: "click",
        });
    }

    for (const attr of attributes) {
        steps.unshift({
            content: `Select value ${attr.value} for attribute ${attr.name}`,
            trigger: `div.attribute-row h2:contains("${attr.name}") + div.row div.col label div.name span:contains("${attr.value}")`,
            run: "click",
        });
    }

    return steps;
}

export function setupCombo(products, addToCart = true) {
    const steps = [];

    for (const product of products) {
        steps.push(clickProduct(product.product));

        if (product.attributes.length > 0) {
            steps.push(...setupAttribute(product.attributes));
        }
    }

    if (addToCart) {
        steps.push({
            content: `Click on 'Add to cart' button`,
            trigger: `.btn.btn-primary`,
            run: "click",
        });
    }

    return steps;
}
