/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";
import {
    adaptForMobile,
    clickLine,
} from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";

class Do {
    clickNewTicket() {
        return [{ trigger: ".ticket-screen .highlight" }];
    }
    clickDiscard() {
        return [
            {
                content: "go back",
                trigger: ".ticket-screen button.discard",
                mobile: false,
            },
            {
                content: "go back",
                trigger: ".pos-rightheader .floor-button",
                mobile: true,
            },
        ];
    }
    clickReview() {
        return [
            {
                content: "click review button",
                trigger: ".btn-switchpane:contains('Review')",
                mobile: true,
            },
        ];
    }
    selectOrder(orderName) {
        return [
            {
                trigger: `.ticket-screen .order-row > .col:contains("${orderName}")`,
            },
        ];
    }
    doubleClickOrder(orderName) {
        return [
            {
                trigger: `.ticket-screen .order-row > .col:nth-child(2):contains("${orderName}")`,
                run: "dblclick",
            },
        ];
    }
    loadSelectedOrder() {
        return [
            {
                content: "click review button",
                trigger: ".btn-switchpane:contains('Review')",
                mobile: true,
            },
            {
                trigger: ".ticket-screen .pads .button.validation.load-order-button",
            },
        ];
    }
    deleteOrder(orderName) {
        return [
            {
                trigger: `.ticket-screen .order-row > .col:contains("${orderName}")`,
                mobile: true,
            },
            {
                trigger: `.ticket-screen .order-row:has(.col:contains("${orderName}")) .delete-button`,
                mobile: true,
            },
            {
                trigger: `.ticket-screen .orders > .order-row > .col:contains("${orderName}") ~ .col[name="delete"]`,
                mobile: false,
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
                trigger: ".pos-search-bar input",
                run: `text ${searchWord}`,
            },
            {
                /**
                 * Manually trigger keyup event to show the search field list
                 * because the previous step do not trigger keyup event.
                 */
                trigger: ".pos-search-bar input",
                run: function () {
                    document
                        .querySelector(".pos-search-bar input")
                        .dispatchEvent(new KeyboardEvent("keyup", { key: "" }));
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
                trigger: ".ticket-screen .buttons .settle-tips",
            },
        ];
    }
    clickControlButton(name) {
        return [
            {
                content: "click review button",
                trigger: ".btn-switchpane:contains('Review')",
                mobile: true,
            },
            {
                trigger: `.ticket-screen .control-button:contains("${name}")`,
            },
        ];
    }
    clickBackToMainTicketScreen() {
        return [
            {
                content: "Go back to main TicketScreen when in mobile",
                trigger: ".pos-rightheader .floor-button",
                mobile: true,
            },
        ];
    }
    clickOrderline(name) {
        return clickLine(name);
    }
    confirmRefund() {
        return [
            {
                content: "click review button",
                trigger: ".btn-switchpane:contains('Review')",
                mobile: true,
            },
            {
                trigger: ".ticket-screen .button.pay-order-button",
            },
        ];
    }
}

class Check {
    checkStatus(orderName, status) {
        return [
            {
                trigger: `.ticket-screen .order-row > .col:contains("${orderName}") ~ .col:nth-child(6):contains(${status})`,
                run: () => {},
                mobile: false,
            },
            {
                trigger: `.ticket-screen .order-row > .col:contains("${orderName}") ~ .col:nth-child(2):contains(${status})`,
                run: () => {},
                mobile: true,
            },
        ];
    }
    hasLine(options) {
        return adaptForMobile(Order.hasLine(options));
    }
    /**
     * Check if the nth row contains the given string.
     * Note that 1st row is the header-row.
     * @param {boolean | undefined} viewMode true if in mobile view, false if in desktop, undefined if in both views.
     */
    nthRowContains(n, string, viewMode = undefined) {
        return [
            {
                trigger: `.ticket-screen .orders > .order-row:nth-child(${n}):contains("${string}")`,
                mobile: viewMode,
                run: () => {},
            },
        ];
    }
    contains(string) {
        return [
            {
                trigger: `.ticket-screen .orders:contains("${string}")`,
                run: () => {},
            },
        ];
    }
    noNewTicketButton() {
        return [
            {
                trigger: ".ticket-screen .controls .buttons:nth-child(1):has(.discard)",
                run: () => {},
            },
        ];
    }
    orderWidgetIsNotEmpty() {
        return adaptForMobile(Order.hasLine());
    }
    filterIs(name) {
        return [
            {
                trigger: `.ticket-screen .pos-search-bar .filter span:contains("${name}")`,
                run: () => {},
            },
        ];
    }
    invoicePrinted() {
        return [
            {
                trigger: '.ticket-screen .control-button:contains("Reprint Invoice")',
                run: () => {},
            },
        ];
    }
    partnerIs(name) {
        return adaptForMobile({
            trigger: `.ticket-screen .set-partner:contains("${name}")`,
            isCheck: true,
        });
    }
    toRefundTextContains(text) {
        return adaptForMobile({
            trigger: `.ticket-screen .to-refund-highlight:contains("${text}")`,
            run: () => {},
        });
    }
    refundedNoteContains(text) {
        return adaptForMobile({
            trigger: `.ticket-screen .refund-note:contains("${text}")`,
            run: () => {},
        });
    }
    tipContains(amount) {
        return [
            {
                trigger: `.ticket-screen .tip-cell:contains("${amount}")`,
                run: () => {},
            },
        ];
    }
    receiptTotalIs(amount) {
        return [
            {
                trigger: `.receipt-screen .pos-receipt-amount:contains("${amount}")`,
                run: () => {},
            },
        ];
    }
}

class Execute {}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("TicketScreen", Do, Check, Execute));
