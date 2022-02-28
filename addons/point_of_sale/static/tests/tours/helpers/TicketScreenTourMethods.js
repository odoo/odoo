odoo.define('point_of_sale.tour.TicketScreenTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');

    class Do {
        clickNewTicket() {
            return [{ trigger: '.ticket-screen .highlight' }];
        }
        clickDiscard() {
            return [{ trigger: '.ticket-screen button.discard' }];
        }
        selectOrder(orderName) {
            return [
                {
                    trigger: `.ticket-screen .order-row > .col:nth-child(2):contains("${orderName}")`,
                },
            ];
        }
        deleteOrder(orderName) {
            return [
                {
                    trigger: `.ticket-screen .orders > .order-row > .col:contains("${orderName}") ~ .col[name="delete"]`,
                },
            ];
        }
        selectFilter(name) {
            return [
                {
                    trigger: `.pos-search-bar .filter`,
                },
                {
                    trigger: `.pos-search-bar .filter ul`,
                    run: () => {},
                },
                {
                    trigger: `.pos-search-bar .filter ul li:contains("${name}")`,
                },
            ];
        }
        search(field, searchWord) {
            return [
                {
                    trigger: '.pos-search-bar input',
                    run: `text ${searchWord}`,
                },
                {
                    /**
                     * Manually trigger keyup event to show the search field list
                     * because the previous step do not trigger keyup event.
                     */
                    trigger: '.pos-search-bar input',
                    run: function () {
                        document
                            .querySelector('.pos-search-bar input')
                            .dispatchEvent(new KeyboardEvent('keyup', { key: '' }));
                    },
                },
                {
                    trigger: `.pos-search-bar .search ul li:contains("${field}")`,
                },
            ];
        }
        settleTips() {
            return [
                {
                    trigger: '.ticket-screen .buttons .settle-tips',
                },
            ];
        }
        clickControlButton(name) {
            return [
                {
                    trigger: `.ticket-screen .control-button:contains("${name}")`,
                },
            ];
        }
        clickOrderline(name) {
            return [
                {
                    trigger: `.ticket-screen .orderline:not(:has(.selected)) .product-name:contains("${name}")`,
                },
                {
                    trigger: `.ticket-screen .orderline.selected .product-name:contains("${name}")`,
                    run: () => {},
                },
            ];
        }
        pressNumpad(key) {
            let trigger;
            if ('.0123456789'.includes(key)) {
                trigger = `.numpad .number-char:contains("${key}")`;
            } else if (key === 'Backspace') {
                trigger = `.numpad .numpad-backspace`;
            } else if (key === '+/-') {
                trigger = `.numpad .numpad-minus`;
            }
            return [
                {
                    trigger,
                },
            ];
        }
        confirmRefund() {
            return [
                {
                    trigger: '.ticket-screen .button.pay',
                },
            ];
        }
    }

    class Check {
        checkStatus(orderName, status) {
            return [
                {
                    trigger: `.ticket-screen .order-row > .col:nth-child(2):contains("${orderName}") ~ .col:nth-child(6):contains(${status})`,
                    run: () => {},
                },
            ];
        }
        /**
         * Check if the nth row contains the given string.
         * Note that 1st row is the header-row.
         */
        nthRowContains(n, string) {
            return [
                {
                    trigger: `.ticket-screen .orders > .order-row:nth-child(${n}):contains("${string}")`,
                    run: () => {},
                },
            ];
        }
        noNewTicketButton() {
            return [
                {
                    trigger: '.ticket-screen .controls .buttons:nth-child(1):has(.discard)',
                    run: () => {},
                },
            ];
        }
        orderWidgetIsNotEmpty() {
            return [
                {
                    trigger: '.ticket-screen:not(:has(.order-empty))',
                    run: () => {},
                },
            ];
        }
        filterIs(name) {
            return [
                {
                    trigger: `.ticket-screen .pos-search-bar .filter span:contains("${name}")`,
                    run: () => {},
                },
            ];
        }
        partnerIs(name) {
            return [
                {
                    trigger: `.ticket-screen .set-partner:contains("${name}")`,
                    run: () => {},
                },
            ];
        }
        toRefundTextContains(text) {
            return [
                {
                    trigger: `.ticket-screen .to-refund-highlight:contains("${text}")`,
                    run: () => {},
               },
            ];
        }
        refundedNoteContains(text) {
            return [
                {
                    trigger: `.ticket-screen .refund-note:contains("${text}")`,
                    run: () => {},
                },
            ];
        }
        tipContains(amount) {
            return [
                {
                    trigger: `.ticket-screen .tip-cell:contains("${amount}")`,
                    run: () => {},
                },
            ];
        }
    }

    class Execute {}

    return createTourMethods('TicketScreen', Do, Check, Execute);
});
