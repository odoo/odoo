/** @odoo-module */

export const PosSelf = {
    check: {
        isNotification: (text) => {
            return {
                content: `Check if there is a notification with ${text}`,
                trigger: `body:has(.o_notification_content:contains('${text}'))`,
                run: () => {},
            };
        },
        isNotNotification: () => {
            return {
                content: "Check if there is a notification",
                trigger: "body:not(:has(.o_notification_content))",
                run: () => {},
            };
        },
        isPrimaryBtn: (buttonName) => {
            return {
                content: `Click on primary button '${buttonName}'`,
                trigger: `.btn:contains('${buttonName}')`,
                run: () => {},
            };
        },
        isNotPrimaryBtn: (buttonName) => {
            return {
                content: `Click on primary button '${buttonName}'`,
                trigger: `.btn:not(:contains('${buttonName}'))`,
                run: () => {},
            };
        },
        isOrderline: (name, price, description = "", attributes = "") => {
            return {
                content: `Verify is there an orderline with ${name} and ${price} and ${description}`,
                trigger: `.o_self_order_item_card:has(.o_self_product_name:contains("${name}")):has(span:contains("${description}")):has(span:contains("${attributes}")):has(span.card-text:contains("${price}"))`,
                run: () => {},
            };
        },
        isNotOrderline: (name, price, description = "", attributes = "") => {
            return {
                content: `Verify is there an orderline with ${name} and ${price} and ${description}`,
                trigger: `.o_self_order_item_card:not(:has(.o_self_product_name:contains("${name}")):has(span:contains("${description}")):has(span:contains("${attributes}")):has(span.card-text:contains("${price}")))`,
                run: () => {},
            };
        },
        isProductQuantity: (name, quantity) => {
            return {
                content: `Verify is there a product with ${name} and ${quantity} selected quantity`,
                trigger: `.o_self_order_item_card .o_self_product_name:contains('${name}') ~ div span.text-primary:contains('${quantity}x')`,
                run: () => {},
            };
        },
        isProductPrice: (name, price) => {
            return {
                content: `Verify is there a product with ${name} and ${price} price`,
                trigger: `.o_self_order_item_card .o_self_product_name:contains('${name}') ~ div span.card-text:contains('${price}')`,
                run: () => {},
            };
        },
        cannotAddProduct: (name) => {
            return [
                {
                    content: `Click on product '${name}'`,
                    trigger: `.o_self_order_item_card .o_self_product_name:contains('${name}')`,
                },
                {
                    content: `Click on 'Add' button`,
                    trigger: `.btn:not(:contains('Add'))`,
                    run: () => {},
                },
            ];
        },
    },
    action: {
        clickBack: () => {
            return {
                content: "Click the navbar back button",
                trigger: "nav.o_self_order_navbar > button",
            };
        },
        clickPrimaryBtn: (buttonName) => {
            return {
                content: `Click on primary button '${buttonName}'`,
                trigger: `.btn:contains('${buttonName}')`,
            };
        },
        addProduct: (name, quantity = 1, description, attributes) => {
            return [
                {
                    content: `Click on product '${name}'`,
                    trigger: `.o_self_order_item_card .o_self_product_name:contains('${name}')`,
                },
                ...quantityHelper(quantity),
                descriptionHelper(description),
                ...attributeHelper(attributes),
                {
                    content: `Click on 'Add' button`,
                    trigger: `.o_self_order_main_button:contains('Add')`,
                },
            ];
        },
        editOrderline: (name, price, description, addQuantity = 0, newDescription, newAtr) => {
            return [
                {
                    content: `Click on orderline ${name}, price ${price} and description ${description}`,
                    trigger: `.o_self_order_item_card:has(.o_self_product_name:contains("${name}")):has(span:contains("${description}")):has(span.card-text:contains("${price}"))`,
                },
                ...quantityHelper(addQuantity),
                descriptionHelper(newDescription),
                ...attributeHelper(newAtr),
                {
                    content: `Click on 'Add' button`,
                    trigger: `.o_self_order_main_button`,
                },
            ];
        },
    },
};

// This function is used to generate the steps to add attributes to a product.
// Missing the color function, but I didn't have example for the moment see in the future.
const attributeHelper = (attributes = { radio: {}, select: {}, color: {} }) => {
    const attributesSteps = [];

    if (attributes.radio.value) {
        attributesSteps.push({
            content: `Select radio ${attributes.radio.name} with value ${attributes.radio.value}`,
            trigger: `.o_self_order_main_options div:contains('${attributes.radio.name}') ~ div input[value='${attributes.radio.value}']`,
        });
    }

    if (attributes.select.value) {
        attributesSteps.push({
            content: `Select radio ${attributes.select.name} with value ${attributes.select.value}`,
            trigger: `.o_self_order_main_options div:contains('${attributes.select.name}') ~ select:has(option[value='${attributes.select.value}'])`,
            run: `text ${attributes.select.value}`,
        });
    }

    return attributesSteps;
};

// This function is used to generate the steps to add a description to a product.
const descriptionHelper = (description = "") => {
    return {
        content: `Add description ${description}`,
        trigger: `.o_self_order_main_options textarea`,
        run: description ? `text ${description}` : () => {},
    };
};

// This function is used to generate the steps to increase the quantity of a product.
const quantityHelper = (quantity, el) => {
    const increaseQuantity = [];

    if (quantity > 0) {
        for (let i = 1; i < quantity; i++) {
            increaseQuantity.push({
                content: `Increase quantity`,
                trigger: `.o_self_order_incr_button .btn:contains('+')`,
            });
        }
    } else {
        for (let i = 0; i > quantity; i--) {
            increaseQuantity.push({
                content: `Decrease quantity`,
                trigger: `.o_self_order_incr_button .btn:contains('-')`,
            });
        }
    }

    return increaseQuantity;
};
