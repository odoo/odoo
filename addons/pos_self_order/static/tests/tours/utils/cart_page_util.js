export function clickBack() {
    return {
        content: `Click on back button`,
        trigger: `.btn.btn-back`,
        run: "click",
    };
}

export function checkNoTableSelector() {
    return {
        content: `Check if the table selection is not displayed`,
        trigger: `body:not(:has(.self_order_popup_table))`,
    };
}

export function selectTable(table) {
    return [
        {
            content: `Select table ${table}`,
            trigger: `.self_order_popup_table select`,
            run: (helpers) => {
                // The default select (run: select 3) doesn't work here
                const options = document.querySelectorAll(".self_order_popup_table option");
                const targetOption = Array.from(options).find((option) =>
                    option.textContent.includes(table)
                );
                const optionValue = targetOption.value;
                helpers.anchor.value = optionValue;
                helpers.anchor.dispatchEvent(new Event("change"));
            },
        },
        {
            content: `Click on 'Confirm' button`,
            trigger: `.self_order_popup_table .btn:contains('Continue with table ${table}')`,
            run: "click",
        },
    ];
}

export function selectRandomValueInInput(inputSelector) {
    return {
        content: `Select Random Value in Input`,
        trigger: inputSelector,
        run: (helpers) => {
            const options = document.querySelectorAll(`${inputSelector} option`);
            for (const option of options) {
                // Verify if the option is not disabled
                if (option.disabled || option.value === "") {
                    continue;
                }

                const targetOption = option;
                const optionValue = targetOption.value;
                helpers.anchor.value = optionValue;
                helpers.anchor.dispatchEvent(new Event("change"));
                break;
            }
        },
    };
}

export function fillInput(inputPlaceholder, value) {
    return {
        content: `Fill input with ${value}`,
        trigger: `input[placeholder="${inputPlaceholder}"]`,
        run: `edit ${value}`,
    };
}

export function checkProduct(name, price, quantity = "1") {
    return {
        content: `Check product card with ${name} and ${price}`,
        trigger: `.product-cart-item:has(div:contains("${name}")):has(div:contains("${quantity}")):has(div .o-so-tabular-nums:contains("${price}"))`,
        run: "click",
    };
}

export function checkAttribute(productName, attributes) {
    let attributeString = "";
    let attributeStringReadable = "";

    for (const attr of attributes) {
        attributeString += `div:contains("${attr.name}: ${attr.value}") +`;
        attributeStringReadable = ` ${attr.name} : ${attr.value},`;
    }

    attributeString = attributeString.slice(0, -1);
    attributeStringReadable = attributeStringReadable.slice(0, -1);

    return {
        content: `Check product card with ${productName} and ${attributeStringReadable}`,
        trigger: `.product-cart-item div:contains("${productName}"):has(${attributeString})`,
        run: "click",
    };
}

export function checkCombo(comboName, products) {
    const steps = [];

    for (const product of products) {
        let step = `.product-cart-item div:contains("${comboName}"):has(div:contains(${product.product}))`;

        if (product.attributes.length > 0) {
            for (const attr of product.attributes) {
                step += `:has(div:contains("${attr.name}") div:contains("${attr.value}"))`;
            }
        }

        steps.push({
            content: `Check combo ${comboName}`,
            trigger: step,
            run: "click",
        });
    }

    return steps;
}

export function checkTotalPrice(price) {
    return {
        content: `The total price to pay is ${price}`,
        trigger: `.order-price :contains(Total):contains(${price})`,
    };
}

export function cancelOrder() {
    return [
        {
            content: `Click on 'Cancel' button`,
            trigger: '.o_self_cart_page .btn:contains("Cancel")',
            run: "click",
        },
        {
            content: `Validate cancel popup`,
            trigger: ".modal-dialog .btn:contains('Cancel Order')",
            run: "click",
        },
    ];
}

export function checkSlotUnavailable(slotValue) {
    return {
        content: `Check that the first available slot is not ${slotValue}`,
        trigger: ".slot-select",
        run: () => {
            const select = document.querySelector(".slot-select");
            // select[0] and select[1] are header values
            if (select[2].innerText === slotValue) {
                throw new Error(`${slotValue} should not be available`);
            }
        },
    };
}

export function isShown() {
    return {
        trigger: `.o_self_cart_page`,
    };
}
