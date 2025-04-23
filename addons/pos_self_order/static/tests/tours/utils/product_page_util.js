export function clickProduct(productName) {
    return {
        content: `Click on product '${productName}'`,
        trigger: `.self_order_product_card span:contains('${productName}')`,
        run: "click",
    };
}

export function checkReferenceNotInProductName(productName, reference) {
    return {
        content: `Check product label has '${productName}' and not ${reference}`,
        trigger: `.self_order_product_card span:contains('${productName}'):not(:contains("${reference}"))`,
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

export function checkAttributePrice(name, value, price) {
    return {
        content: `Check product price ${price} for variant ${name}: ${value}`,
        trigger: `div.attribute-row h2:contains('${name}') + div.row div.col label div.name span:contains('${value}') + span:contains('${price}')`,
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

export function verifyIsCheckedAttribute(attribute, values = []) {
    return {
        content: `Select value for attribute ${attribute}`,
        trigger: `div.attribute-row h2:contains("${attribute}")`,
        run: () => {
            const attributesValues = Array.from(
                document.querySelectorAll("div.attribute-row h2")
            ).find((el) => el.textContent.includes(attribute));
            if (!attributesValues) {
                throw Error(`${attribute} not found.`);
            }
            const rowDiv = attributesValues.nextElementSibling;
            if (!rowDiv || !rowDiv.matches("div.row")) {
                throw Error("Sibling div.row not found or is incorrect.");
            }
            const colDiv = rowDiv.querySelector("div.col");
            const labelElement = colDiv ? colDiv.querySelector("label") : null;
            const inputElement = colDiv ? colDiv.querySelector("input") : null;
            if (!labelElement || !inputElement) {
                throw Error(`Missing ${attribute} values`);
            }
            const attributeValue = labelElement.querySelector("div > span").textContent.trim();
            if (values.includes(attributeValue) && !inputElement.checked) {
                throw Error(`Attribute ${attributeValue} not checked`);
            }
        },
    };
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
