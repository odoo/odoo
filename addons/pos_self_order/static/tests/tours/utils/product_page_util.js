export function clickProduct(productName) {
    return {
        content: `Click on product '${productName}'`,
        trigger: `.self_order_product_card span:contains('${productName}')`,
        run: "click",
    };
}

export function clickKioskProduct(productName) {
    return {
        content: `Click on product '${productName}'`,
        trigger: `.o_kiosk_product_box span:contains('${productName}')`,
        run: "click",
    };
}

export function clickKioskCategory(categoryName) {
    return {
        content: `Click on category '${categoryName}'`,
        trigger: `.category_btn:contains('${categoryName}')`,
        run: "click",
    };
}

export function waitProduct(productName) {
    return {
        content: `Wait for product '${productName}'`,
        trigger: `.self_order_product_card span:contains('${productName}')`,
    };
}

export function checkReferenceNotInProductName(productName, reference) {
    return {
        content: `Check product label has '${productName}' and not ${reference}`,
        trigger: `.self_order_product_card span:contains('${productName}'):not(:contains("${reference}"))`,
    };
}

export function checkKioskReferenceNotInProductName(productName, reference) {
    return {
        content: `Check product label has '${productName}' and not ${reference}`,
        trigger: `.o_kiosk_product_box span:contains('${productName}'):not(:contains("${reference}"))`,
    };
}

export function clickBack() {
    return {
        content: `Click on back button`,
        trigger: `.btn.btn-back`,
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
            trigger: `.btn.btn-primary:contains('Cancel Order')`,
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

export function clickKioskComboDiscard() {
    return {
        content: "Click on Discard button",
        trigger: ".btn.btn-link .oi-close",
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

export function setupKioskAttribute(attributes, addToCart = true) {
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
            trigger: `h2:contains("${attr.name}") + .attribute_list button:contains("${attr.value}")`,
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

export function setupKioskCombo(products, addToCart = true) {
    const steps = [];

    for (const product of products) {
        steps.push(clickKioskProduct(product.product));

        if (product.attributes.length > 0) {
            steps.push(...setupKioskAttribute(product.attributes));
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
