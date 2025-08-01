export function clickProduct(productName) {
    return {
        content: `Click on product '${productName}'`,
        trigger: `.o_self_product_box span:contains('${productName}')`,
        run: "click",
    };
}
export function clickCategory(categoryName) {
    return {
        content: `Click on category '${categoryName}'`,
        trigger: `.category_btn:contains('${categoryName}')`,
        run: "click",
    };
}

export function waitProduct(productName) {
    return {
        content: `Wait for product '${productName}'`,
        trigger: `.o_self_product_box span:contains('${productName}')`,
    };
}

export function checkReferenceNotInProductName(productName, reference) {
    return {
        content: `Check product label has '${productName}' and not ${reference}`,
        trigger: `.o_self_product_box span:contains('${productName}'):not(:contains("${reference}"))`,
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
            trigger: `h2:contains("${attr.name}") + div.row button:contains("${attr.value}")`,
            run: "click",
        });
    }

    return steps;
}

export function verifyIsCheckedAttribute(attribute, values = []) {
    return {
        content: `Select value for attribute ${attribute}`,
        trigger: `div h2:contains("${attribute}")`,
        run: () => {
            const attributesValues = Array.from(document.querySelectorAll("div h2")).find((el) =>
                el.textContent.includes(attribute)
            );
            if (!attributesValues) {
                throw Error(`${attribute} not found.`);
            }
            const rowDiv = attributesValues.nextElementSibling;
            if (!rowDiv || !rowDiv.matches("div.row")) {
                throw Error("Sibling div.row not found or is incorrect.");
            }

            const selectedButtons = rowDiv.querySelectorAll(".o_self_box_selected");
            // Extract text content of selected buttons
            const selectedValues = Array.from(selectedButtons).map((btn) =>
                btn.querySelector("span")?.textContent.trim()
            );

            // Check if all expected values are selected
            for (const val of values) {
                if (!selectedValues.includes(val)) {
                    throw new Error(
                        `Expected value "${val}" for attribute "${attribute}" is not selected.`
                    );
                }
            }

            // Optionally, verify that no unexpected values are selected
            if (selectedValues.length !== values.length) {
                throw new Error(
                    `Mismatch in selected values for attribute "${attribute}". Expected: ${values.join(
                        ", "
                    )}, Found: ${selectedValues.join(", ")}`
                );
            }
        },
    };
}

export function clickComboProduct(productName) {
    return {
        content: `Click on combo product '${productName}'`,
        trigger: `.combo_product_box span:contains('${productName}')`,
        run: "click",
    };
}

export function setupCombo(products, addToCart = true) {
    const steps = [];

    for (const product of products) {
        steps.push(clickComboProduct(product.product));

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

export function checkProductOutOfStock(productName) {
    return {
        content: `Check if '${productName}' is marked as out of stock`,
        trigger: `.o_self_product_box:has(span:contains('${productName}')):has(div:contains('Out of stock'))`,
    };
}
