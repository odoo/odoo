/** @odoo-module */

export function clickBack() {
    return {
        content: `Click on back button`,
        trigger: `.btn.btn-back`,
    };
}

export function selectTable(table) {
    return [
        {
            content: `Select table ${table}`,
            trigger: `.self_order_popup_table select:has(option:contains("${table}"))`,
            run: `text ${table}`,
        },
        {
            content: `Click on 'Confirm' button`,
            trigger: `.self_order_popup_table .btn:contains('Confirm')`,
        },
    ];
}

export function checkProduct(name, price, quantity) {
    return {
        content: `Check product card with ${name} and ${price}`,
        trigger: `.product-card-item:has(strong:contains("${name}")):has(div:contains("${quantity}")):has(div .o-so-tabular-nums:contains("${price}"))`,
    };
}

export function checkAttribute(productName, attributes) {
    let attributeString = "";
    let attributeStringReadable = "";

    for (const attr of attributes) {
        attributeString += `div:contains("${attr.name} : ${attr.value}") +`;
        attributeStringReadable = ` ${attr.name} : ${attr.value},`;
    }

    attributeString = attributeString.slice(0, -1);
    attributeStringReadable = attributeStringReadable.slice(0, -1);

    return {
        content: `Check product card with ${productName} and ${attributeStringReadable}`,
        trigger: `.product-card-item div:contains("${productName}") + div ${attributeString}`,
    };
}

export function checkCombo(comboName, products) {
    const steps = [];

    for (const product of products) {
        let step = `.product-card-item div:contains("${comboName}"):has(div div.small div:contains(${product.product}))`;

        if (product.attributes.length > 0) {
            for (const attr of product.attributes) {
                step += `:has(div:contains("${attr.name}") div:contains("${attr.value}"))`;
            }
        }

        steps.push({
            content: `Check combo ${comboName}`,
            trigger: step,
        });
    }

    return steps;
}

export function cancelOrder() {
    return [
        {
            content: `Click on 'Cancel' button`,
            trigger: '.order-cart-content .btn:contains("Cancel")',
        },
        {
            content: `Validate cancel popup`,
            trigger: ".modal-dialog .btn:contains('Cancel Order')",
        },
    ];
}
