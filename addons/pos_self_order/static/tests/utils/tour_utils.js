/** @odoo-module */

/**
 * @typedef {object} TourStep
 * @property {string} content
 * @property {string} trigger
 * @property {boolean?} isCheck
 */

/**
 * @typedef {object} Attribute
 * @property {string} type
 * @property {string} name
 * @property {string} value
 */
import { TourError } from "@web_tour/tour_service/tour_utils";

export const PosSelf = {
    check: {
        tablePopupIsShown: () => {
            return {
                content: `Check if the select table popup is shown`,
                trigger: `body:has(.o_self-popup-table)`,
                run: () => {},
            };
        },
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
        isOrderline: (name, price, description = "", attributes = "", click = false) => {
            let trigger = `.o_self_order_item_card:has(.o_self_product_name:contains("${name}"))`;
            if (description) {
                trigger += `:has(span.customer_note:contains("${description}"))`;
            }
            if (price) {
                trigger += `:has(span.line_price:contains("${price}"))`;
            }
            if (attributes) {
                trigger += `:has(span:contains("${attributes}"))`;
            }
            return {
                content: `${
                    (click && "Click") || "Check"
                } orderline with ${name} and ${price} and ${description}`,
                trigger: trigger,
                isCheck: !click,
            };
        },
        isKioskOrderline: (name, price, qty) => {
            return {
                content: `Verify is there an orderline with ${name} and ${price} and ${qty}`,
                trigger: `.o_kiosk_item_card:has(.o_kiosk_product_name:contains("${name}")):has(span.fw-bolder:contains("${price}")):has(div.d-flex:contains("${qty}"))`,
                run: () => {},
            };
        },
        isNotKioskOrderline: (name) => {
            return {
                content: `Verify is there no orderline with ${name}`,
                trigger: `.o_kiosk_item_card`,
                run: () => {
                    const product = Array.from(document.querySelectorAll('div')).find(el => el.textContent === `${name}`);
                    if (product){
                        throw new TourError(`${name} should not be present in the order`);
                    }
                },
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
                    content: `Inside product main view 'Add' button should not be present`,
                    trigger: `body:not(:has(.product_main_view .o_self_order_main_button))`,
                },
            ];
        },
        isNoOrderInHistory: () => {
            return {
                content: `Verify if there is no order in history`,
                trigger: `.justify-content-center:contains('No order found')`,
                run: () => {},
            };
        },
        attributes: (attributes) => attributes.map((attribute) => attributeHelper(attribute, true)),
        isPreparingOrder: () => {
            return {
                content: `Verify if the order is preparing`,
                trigger: `body:has(.o_kiosk_preparation_title:contains('preparing'))`,
                run: () => {},
            }
        },
        isTableNumber: (number) => {
            return {
                content: `Verify if right table is selected`,
                trigger: `body:has(.number:contains('${number}'))`,
                run: () => {},
            }
        },
    },
    action: {
        cancelOrder: () => {
            return [
                {
                    content: `Toggle 'Cancel' button`,
                    trigger: `.o_self-cancel-toggle-btn`,
                },
                {
                    content: `Click on 'Cancel' button`,
                    trigger: `.o_self-cancel-btn`,
                },
            ];
        },
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
        clickCancelPopupBtn: () => {
            return {
                trigger: `.btn:contains('Cancel Order')`,
                in_modal: true,
            };
        },
        selectTable(table) {
            return {
                content: `Select ${table.name} with value ${table.id}`,
                trigger: `.o_self-popup-table select:has(option[value='${table.id}'])`,
                run: `text ${table}`,
            };
        },
        clicKioskProduct: (name) => {
            return [
                {
                    content: `Click on product '${name}'`,
                    trigger: `.o_kiosk_product_card span:contains('${name}')`,
                },
            ]
        },
        addProduct: (name, quantity = 1, description, attributes = []) => {
            return [
                {
                    content: `Click on product '${name}'`,
                    trigger: `.o_self_order_item_card .o_self_product_name:contains('${name}')`,
                },
                ...quantityHelper(quantity),
                descriptionHelper(description),
                ...attributes.map((attribute) => attributeHelper(attribute)),

                {
                    content: `Click on 'Add' button`,
                    trigger: `.o_self_order_main_button:contains('Add')`,
                },
            ];
        },
        editSentOrderline: (name, price, description, addQuantity = 0) => {
            return [
                clickOrderline(name, price, description),
                ...quantityHelper(addQuantity),
                {
                    content: `Click on 'Add' button`,
                    trigger: `.o_self_order_main_button`,
                },
            ];
        },
        clickOrderline: clickOrderline,

        editOrderline: (name, price, description, addQuantity = 0, newDescription) => {
            return [
                clickOrderline(name, price, description),
                ...quantityHelper(addQuantity),
                descriptionHelper(newDescription),
                {
                    content: `Click on 'Add' button`,
                    trigger: `.o_self_order_main_button`,
                },
            ];
        },
        selectAttributes: (attributes) => attributes.map((attribute) => attributeHelper(attribute)),
        clickKioskTrash: (name) => {
            return [
                {
                    content: `Click on trash icon`,
                    trigger: `.o_kiosk_item_card:has(.o_kiosk_product_name:contains("${name}")) .btn .fa.fa-trash`,
                }
            ];
        },
        pressNumpad: (keys) => {
            const numberChars = "0 1 2 3 4 5 6 7 8 9".split(" ");
            function generateStep(key) {
                let trigger;
                if (numberChars.includes(key)) {
                    trigger = `.numpad .touch-key:contains("${key}")`;
                }
                return {
                    content: `'${key}' pressed in numpad`,
                    trigger,
                };
            }
            return keys.split(" ").map(generateStep);
        },
        selectLocation: (location) => {
            return {
                content: `Select location: ${location}`,
                trigger: `.o_kiosk_eating_location span:contains('${location}')`
            }
        }
    },
};

/**
// This function is used to generate the steps to add attributes to a product.
// Missing the color function, but I didn't have example for the moment see in the future.
 * @param {Attribute} attribute
 * @param {boolean} [isCheck=false]
 * @returns {TourStep}
 */
function attributeHelper(attribute, isCheck = false) {
    const content = `${isCheck ? "Check" : "Select"} ${attribute.name} with value ${
        attribute.value
    }`;
    const attributeDiv = `.o_self_order_main_options div:contains('${attribute.name}')`;
    if (attribute.type === "radio") {
        const radioInput = `${attributeDiv} ~ div input[name='${attribute.value}']`;
        return {
            content,
            trigger: radioInput + (isCheck ? ":checked" : ""),
            isCheck,
        };
    } else if (attribute.type === "select") {
        const selectInput = `${attributeDiv} ~ select:has(option[name='${attribute.value}'])`;
        const selectInputSelected = `${selectInput.slice(0, -1)}[selected])`;
        return {
            content,
            trigger: isCheck ? selectInputSelected : selectInput,
            run: isCheck ? () => {} : `text ${attribute.value}`,
        };
    }
}

// This function is used to generate the steps to add a description to a product.
export const descriptionHelper = (description = "") => {
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
function clickOrderline(name, price, description) {
    return PosSelf.check.isOrderline(name, price, description, false, true);
}
