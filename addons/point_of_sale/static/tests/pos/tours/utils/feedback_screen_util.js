/* global posmodel */

import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";

export function clickNextOrder() {
    return [
        ...isContinueEnabled(),
        {
            content: "go to next screen",
            trigger: ".feedback-screen .button.validation",
            run: "click",
        },
    ];
}
export function isContinueEnabled() {
    return [
        {
            content: "wait for next order button to be enabled",
            trigger: ".feedback-screen .button.validation:not([disabled])",
        },
    ];
}
export function isTransitioning() {
    return [
        {
            content: "wait for next order button to be in transitioning state",
            trigger: ".feedback-screen .button.validation .wipe-overlay",
        },
    ];
}
export function clickScreen() {
    return [
        {
            content: "click on feedback screen",
            trigger: ".feedback-screen",
            run: "click",
        },
    ];
}

export function isShown() {
    return [
        {
            content: "feedback screen is shown",
            trigger: ".pos .feedback-screen",
        },
    ];
}
export function totalAmountContains(value) {
    return [
        {
            content: `total amount contains ${value}`,
            trigger: `.feedback-screen .amount-container.amount:contains("${value}")`,
        },
    ];
}

export function checkTicketData(data, basic = false) {
    // data is an object like:
    // {
    //   total_amount,
    //   is_rounding,
    //   rounding_amount,
    //   is_to_pay,
    //   to_pay_amount,
    //   is_change,
    //   change_amount,
    //   is_discount,
    //   is_shipping_date,
    //   is_shipping_date_today,
    //   is_cashier,
    //   cashier_name,
    //   is_qr_code,
    //   payment_lines: [{
    // 	  name,
    // 	  amount,
    //   }],
    //   orderlines: [{
    // 	  name,
    // 	  quantity,
    // 	  price_unit,
    // 	  line_price,
    // 	  cssRules (array with other things to check): [{
    //      css: ".some-css-selector",
    //      text: "text that should be in the element",
    //      negation: true/false (if true, the text should NOT be in the element)
    //      length: number of elements that should be found with the css selector
    //     }],
    //   }],
    //   cssRules (array with other things to check): [{
    //     css: ".some-css-selector",
    //     text: "text that should be in the element",
    //     negation: true/false (if true, the text should NOT be in the element)
    //     length: number of elements that should be found with the css selector
    //   }],
    // }
    const check = async (data, basic) => {
        const generator = posmodel.getOrderReceiptGenerator(posmodel.getOrder(), basic);
        const ticket = await generator.generateHtml();

        if (!ticket && !Object.keys(data).length) {
            return true;
        }

        if (data.total_amount) {
            ticket.querySelector(".total-amount").innerHTML.includes(data.total_amount);
        }

        if (data.is_rounding || data.rounding_amount) {
            if (!ticket.querySelector(".rounding-amount")) {
                throw new Error("No rounding amount has been found in receipt.");
            }
            if (data.rounding_amount) {
                ticket.querySelector(".rounding-amount").innerHTML.includes(data.rounding_amount);
            }
        } else if (data.is_rounding === false) {
            if (ticket.querySelector(".rounding-amount")) {
                throw new Error("A rounding amount has been found in receipt.");
            }
        }

        if (data.is_to_pay || data.to_pay_amount) {
            if (!ticket.querySelector(".total-amount")) {
                throw new Error("No amount to pay has been found in receipt.");
            }
            if (data.to_pay_amount) {
                ticket.querySelector(".total-amount").innerHTML.includes(data.to_pay_amount);
            }
        } else if (data.is_to_pay === false) {
            if (ticket.querySelector(".total-amount")) {
                throw new Error("An amount to pay has been found in receipt.");
            }
        }

        if (data.is_change || data.change_amount) {
            if (!ticket.querySelector(".change-amount")) {
                throw new Error("No change amount has been found in receipt.");
            }
            if (data.change_amount) {
                ticket.querySelector(".change-amount").innerHTML.includes(data.change_amount);
            }
        } else if (data.is_change === false) {
            if (ticket.querySelector(".change-amount")) {
                throw new Error("A change amount has been found in receipt.");
            }
        }

        if (data.is_discount) {
            if (!ticket.querySelector(".discount-amount")) {
                throw new Error("No discount amount has been found in receipt.");
            }
        } else if (data.is_discount === false) {
            if (ticket.querySelector(".discount-amount")) {
                throw new Error("A discount amount has been found in receipt.");
            }
        }

        if (data.is_shipping_date || data.is_shipping_date_today) {
            if (!ticket.querySelector(".shipping-date")) {
                throw new Error("No shipping date has been found in receipt.");
            }
            if (data.is_shipping_date_today) {
                const expectedDelivery = new Date().toLocaleString(
                    "en-US",
                    luxon.DateTime.DATE_SHORT
                );
                ticket.querySelector(".shipping-date").innerHTML.includes(expectedDelivery);
            }
        } else if (data.is_shipping_date === false) {
            if (ticket.querySelector(".shipping-date")) {
                throw new Error("A shipping date has been found in receipt.");
            }
        }

        if (data.is_cashier || data.cashier_name) {
            if (!ticket.querySelector(".cashier-name")) {
                throw new Error("No cashier name has been found in receipt.");
            }
            if (data.cashier_name) {
                ticket.querySelector(".cashier-name").innerHTML.includes(data.cashier_name);
            }
        } else if (data.is_cashier === false) {
            if (ticket.querySelector(".cashier-name")) {
                throw new Error("A cashier name has been found in receipt.");
            }
        }

        if (data.is_qr_code) {
            if (!ticket.querySelector(".invoice-qr-code")) {
                throw new Error("No QR code has been found in receipt.");
            }
        } else if (data.is_qr_code === false) {
            if (ticket.querySelector(".invoice-qr-code")) {
                throw new Error("A QR code has been found in receipt.");
            }
        }

        if (data.payment_lines) {
            const paymentLines = ticket.querySelectorAll(".payment-line");

            for (const [index, line] of data.payment_lines.entries()) {
                const paymentLine = paymentLines[index];
                if (!paymentLine) {
                    throw new Error(`No payment line found for ${line.name}`);
                }
                const name = paymentLine.firstChild.textContent;
                if (line.name != name) {
                    throw new Error(
                        `Payment line name mismatch: expected ${line.name}, got ${name}`
                    );
                }

                if (line.amount) {
                    const amount = paymentLine.lastChild.textContent;
                    if (!amount.includes(line.amount)) {
                        throw new Error(
                            `Payment line amount mismatch for ${line.name}: expected ${line.amount}, got ${amount}`
                        );
                    }
                }
            }
        }

        if (data.orderlines) {
            const lines = ticket.querySelectorAll(".lines");

            for (const [index, line] of data.orderlines.entries()) {
                const orderline = lines[index];
                if (!orderline) {
                    throw new Error(`No order line found for ${line.name}`);
                }
                const name = orderline.querySelector(".name").textContent;
                if (!name.includes(line.name)) {
                    throw new Error(
                        `Order line name mismatch: expected ${line.name}, got ${name}.`
                    );
                }

                if (line.quantity) {
                    const qty = orderline.querySelector(".qty").textContent;
                    if (line.quantity != qty) {
                        throw new Error(
                            `Order line quantity mismatch for ${name}: expected ${line.quantity}, got ${qty}.`
                        );
                    }
                }

                if (basic) {
                    if (
                        orderline.querySelector(".price-unit") ||
                        orderline.querySelector(".price-incl")
                    ) {
                        throw new Error("The price should not be included on a basic receipt");
                    }
                } else {
                    if (line.price_unit) {
                        const price_unit = orderline.querySelectorAll(".price-unit");
                        if (price_unit.length === 0) {
                            throw new Error(
                                `No price per unit found for order line ${name} in receipt.`
                            );
                        }
                        const priceFound = [...price_unit].some((p) =>
                            p.textContent.includes(line.price_unit)
                        );
                        if (!priceFound) {
                            throw new Error(
                                `Order line price per unit mismatch for ${name}: expected ${line.price_unit}.`
                            );
                        }
                    }

                    if (line.line_price) {
                        const line_price = orderline.querySelector(".price-incl").textContent;
                        if (!line_price.includes(line.line_price)) {
                            throw new Error(
                                `Order line price mismatch for ${name}: expected ${line.line_price}, got ${line_price}.`
                            );
                        }
                    }
                }

                if (line.cssRules) {
                    for (const rule of line.cssRules) {
                        const statement = orderline.querySelectorAll(rule.css);
                        if (!statement && rule.negation) {
                            continue; // No statement found and negation is true so the rule is validated
                        }
                        if (!statement) {
                            throw new Error(`CSS rule ${rule.css} not found in receipt.`);
                        }
                        if (rule.length && rule.length !== statement.length) {
                            throw new Error(
                                `CSS rule ${rule.css} length mismatch: expected ${rule.length} elements, got ${statement.length}.`
                            );
                        }
                        if (rule.text) {
                            const ruleFound = [...statement].some((s) =>
                                s.textContent.includes(rule.text)
                            );
                            if (ruleFound == rule.negation) {
                                throw new Error(`Rule ${rule.css} not found in printed receipt.`);
                            }
                        }
                    }
                }
            }
        }

        if (data.cssRules) {
            for (const rule of data.cssRules) {
                const statement = ticket.querySelectorAll(rule.css);
                if (!statement && rule.negation) {
                    continue; // No statement found and negation is true so the rule is validated
                }
                if (!statement) {
                    throw new Error(`CSS rule ${rule.css} not found in receipt.`);
                }
                if (rule.text) {
                    const ruleFound = [...statement].some((s) => s.textContent.includes(rule.text));
                    if (ruleFound == rule.negation) {
                        throw new Error(`Rule ${rule.css} not found in printed receipt.`);
                    }
                }
            }
        }

        return true;
    };

    return [
        {
            trigger: "body",
            run: async () => await check(data, basic),
        },
    ];
}
export function trackingMethodIsLot(lot) {
    return [
        {
            content: `tracking method is Lot`,
            trigger: `li.lot-number:contains("Lot Number ${lot}")`,
            run: function () {
                if (document.querySelectorAll("li.lot-number").length !== 1) {
                    throw new Error(`Expected exactly one 'Lot Number ${lot}' element.`);
                }
            },
        },
    ];
}

export function clickSendButton() {
    return [
        {
            content: "click on send button",
            trigger: ".feedback-screen button.send-receipt",
            run: "click",
        },
    ];
}

export function setEmail(email) {
    return [
        {
            content: "set email",
            trigger: ".modal-body .send-receipt-email-input",
            run: `edit ${email}`,
        },
    ];
}

export function clickEmailButton() {
    return [
        {
            content: "send email",
            trigger: ".modal-body .fa-paper-plane",
            run: "click",
        },
    ];
}

export function emailIsSuccessful() {
    return [
        {
            trigger: `.modal-body .notice .text-success`,
        },
    ];
}

export function sendEmail(email, expectSuccess = true) {
    return [
        ...clickSendButton(),
        ...setEmail(email),
        ...clickEmailButton(),
        ...(expectSuccess ? emailIsSuccessful() : []),
        Dialog.cancel(),
    ];
}

function clickPrintButton() {
    return [
        {
            content: "click on print button",
            trigger: ".feedback-screen button.print-ticket-button",
            run: "click",
        },
    ];
}

export function clickEditPayment() {
    return [
        {
            trigger: ".feedback-screen .edit-order-payment:contains(Edit)",
            run: "click",
        },
    ];
}

export function printTicket(ticketLabel) {
    return [
        ...clickPrintButton(),
        {
            content: `print ${ticketLabel} ticket`,
            trigger: `.modal-body button:contains(${ticketLabel})`,
            run: "click",
        },
    ];
}
