odoo.define('point_of_sale.tour.ReceiptScreenTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');

    class Do {
        clickNextOrder() {
            return [
                {
                    content: 'go to next screen',
                    trigger: '.receipt-screen .button.next.highlight',
                },
            ];
        }
        setEmail(email) {
            return [
                {
                    trigger: '.receipt-screen .input-email input',
                    run: `text ${email}`,
                },
            ];
        }
        clickSend(isHighlighted = true) {
            return [
                {
                    trigger: `.receipt-screen .input-email .send${isHighlighted ? '.highlight' : ''}`,
                },
            ];
        }
        clickBack() {
            return [
                {
                    trigger: '.receipt-screen .button.back',
                },
            ];
        }
    }

    class Check {
        isShown() {
            return [
                {
                    content: 'receipt screen is shown',
                    trigger: '.pos .receipt-screen',
                    run: () => {},
                },
            ];
        }

        receiptIsThere() {
            return [
                {
                    content: 'there should be the receipt',
                    trigger: '.receipt-screen .pos-receipt',
                    run: () => {},
                },
            ];
        }

        totalAmountContains(value) {
            return [
                {
                    trigger: `.receipt-screen .top-content h1:contains("${value}")`,
                    run: () => {},
                },
            ];
        }

        emailIsSuccessful() {
            return [
                {
                    trigger: `.receipt-screen .notice .successful`,
                    run: () => {},
                },
            ];
        }

        customerNoteIsThere(note) {
            return [
                {
                    trigger: `.receipt-screen .orderlines .pos-receipt-left-padding:contains("${note}")`
                }
            ]
        }
        discountAmountIs(value) {
            return [
                {
                    trigger: `.pos-receipt>div:contains("Discounts")>span:contains("${value}")`,
                    run: () => {},
                },
            ];
        }
        noDiscountAmount() {
            return [
                {
                    trigger: `.pos-receipt:not(:contains("Discounts"))`,
                    run: () => {},
                },
            ];
        }
        noOrderlineContainsDiscount() {
            return [
                {
                    trigger: `.orderlines:not(:contains('->'))`,
                    run: () => { },
                },
            ];
        }
        trackingMethodIsLot() {
            return [
                {
                    content: `tracking method is Lot`,
                    trigger: `li:contains("Lot Number")`,
                    run: () => {},
                },
            ];
        }
    }

    class Execute {
        nextOrder() {
            return [...this._check.isShown(), ...this._do.clickNextOrder()];
        }
    }

    return createTourMethods('ReceiptScreen', Do, Check, Execute);
});
