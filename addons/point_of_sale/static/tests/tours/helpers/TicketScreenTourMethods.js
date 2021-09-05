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
                     * Manually trigger keydown event to show the search field list
                     * because the previous step do not trigger keydown event.
                     */
                    trigger: '.pos-search-bar input',
                    run: function () {
                        document
                            .querySelector('.pos-search-bar input')
                            .dispatchEvent(new KeyboardEvent('keydown', { key: '' }));
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
    }

    class Execute {}

    return createTourMethods('TicketScreen', Do, Check, Execute);
});
