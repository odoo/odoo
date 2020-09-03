odoo.define('point_of_sale.tour.OrderManagementScreenTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');

    class Do {
        clickBack() {
            return [
                {
                    content: 'order management screen, click back button',
                    trigger: '.order-management-screen .control-panel .button.back',
                },
            ];
        }
        clickOrder(name, [otherCol, otherColVal] = [null, null]) {
            let trigger = `.order-management-screen .order-list .order-row .item.name:contains("${name}")`;
            if (otherCol) {
                trigger = `${trigger} ~ .item.${otherCol}:contains("${otherColVal}")`;
            }
            return [
                {
                    content: `clicking order '${name}' from orderlist`,
                    trigger,
                },
            ];
        }
        clickInvoiceButton() {
            return [
                {
                    content: 'click invoice button',
                    trigger: '.order-management-screen .control-button span:contains("Invoice")',
                },
            ];
        }
        clickPrintReceiptButton() {
            return [
                {
                    content: 'click reprint receipt button',
                    trigger: '.order-management-screen .control-button span:contains("Print Receipt")'
                }
            ]
        }
        clickCustomerButton() {
            return [
                {
                    content: 'click customer button',
                    trigger: '.order-management-screen .actionpad .button.set-customer',
                },
            ];
        }
        closeReceipt() {
            return [
                {
                    content: 'close receipt',
                    trigger: '.receipt-screen .button.back',
                }
            ]
        }
    }

    class Check {
        isShown() {
            return [
                {
                    content: 'order management screen is shown',
                    trigger: '.pos .pos-content .order-management-screen',
                    run: () => {},
                },
            ];
        }
        orderlistHas({ orderName, total, customer }) {
            const steps = [];
            steps.push({
                content: `order list has row having: name '${orderName}', total '${total}'`,
                trigger: `.order-list .order-row .item:contains("${orderName}") ~ .item:contains("${total}")`,
                run: () => {},
            });
            if (customer) {
                steps.push({
                    content: `order list has row having: name '${orderName}', customer '${customer}'`,
                    trigger: `.order-list .order-row .item:contains("${orderName}") ~ .item:contains("${customer}")`,
                    run: () => {},
                });
            }
            return steps;
        }
        highlightedOrderRowHas(name) {
            return [
                {
                    content: `order '${name}' in orderlist is highligted`,
                    trigger: `.order-list .order-row.highlight:has(> .item:contains("${name}"))`,
                    run: () => {},
                },
            ];
        }
        orderRowIsNotHighlighted(name) {
            return [
                {
                    content: `order '${name}' in orderlist is not highligted`,
                    trigger: `.order-list .order-row:not(:has(.highlight)):has(> .item:contains("${name}"))`,
                    run: () => {},
                },
            ];
        }
        orderDetailsHas({ lines, total }) {
            const steps = [];
            for (let { product, quantity } of lines) {
                steps.push({
                    content: `order details has product '${product}' and quantity '${quantity}'`,
                    trigger: `.orderlines .product-name:contains("${product}") ~ .info strong:contains("${quantity}")`,
                    run: () => {},
                });
            }
            if (total) {
                steps.push({
                    content: `order details has total amount of ${total}`,
                    trigger: `.order-container .summary .total .value:contains("${total}")`,
                    run: () => {},
                });
            }
            return steps;
        }
        customerIs(name) {
            return [
                {
                    content: `set customer is '${name}'`,
                    trigger: `.order-management-screen .actionpad .set-customer:contains("${name}")`,
                    run: () => {},
                },
            ];
        }
        reprintReceiptIsShown() {
            return [
                {
                    content: 'reprint receipt screen is shown',
                    trigger: '.pos .receipt-screen',
                    run: () => {},
                }
            ]
        }
        receiptChangeIs(amount) {
            return [
                {
                    content: `receipt change is ${amount}`,
                    trigger: `.pos-receipt-amount.receipt-change:contains("${amount}")`,
                    run: () => {},
                }
            ]
        }
        receiptOrderDataContains(orderInfo) {
            return [
                {
                    content: `order data contains ${orderInfo}`,
                    trigger: `.pos-receipt-order-data:contains("${orderInfo}")`,
                    run: () => {},
                }
            ]
        }
        receiptAmountIs(amount) {
            return [
                {
                    content: `receipt amount is ${amount}`,
                    trigger: `.pos-receipt-amount:contains("${amount}")`,
                    run: () => {},
                }
            ]
        }
        isNotHidden() {
            return [
                {
                    content: 'order management screen is not hidden',
                    trigger: `.order-management-screen:not(:has(.oe_hidden))`,
                    run: () => {},
                }
            ]
        }
    }

    return createTourMethods('OrderManagementScreen', Do, Check);
});
