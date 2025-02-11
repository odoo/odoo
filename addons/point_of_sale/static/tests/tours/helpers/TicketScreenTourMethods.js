/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { inLeftSide } from "@point_of_sale/../tests/tours/helpers/utils";

export function clickNewTicket() {
    return [{ trigger: ".ticket-screen .highlight" }];
}
export function clickDiscard() {
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
export function selectOrder(orderName) {
    return [
        {
            trigger: `.ticket-screen .order-row > .col:contains("${orderName}")`,
        },
    ];
}
export function doubleClickOrder(orderName) {
    return [
        {
            trigger: `.ticket-screen .order-row > .col:nth-child(2):contains("${orderName}")`,
            run: "dblclick",
        },
    ];
}
export function loadSelectedOrder() {
    return [
        ProductScreen.clickReview(),
        {
            trigger: ".ticket-screen .pads .button.validation.load-order-button",
        },
    ];
}
export function deleteOrder(orderName) {
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
export function selectFilter(name) {
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
export function search(field, searchWord) {
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
export function settleTips() {
    return [
        {
            trigger: ".ticket-screen .buttons .settle-tips",
        },
    ];
}
export function clickControlButton(name) {
    return [
        ProductScreen.clickReview(),
        {
            trigger: `.ticket-screen .control-button:contains("${name}")`,
        },
    ];
}
export function clickBackToMainTicketScreen() {
    return [
        {
            content: "Go back to main TicketScreen when in mobile",
            trigger: ".pos-rightheader .floor-button",
            mobile: true,
        },
    ];
}
export function confirmRefund() {
    return [
        ProductScreen.clickReview(),
        {
            trigger: ".ticket-screen .button.pay-order-button",
        },
    ];
}
export function checkStatus(orderName, status) {
    return [
        {
            trigger: `.ticket-screen .order-row > .col:contains("${orderName}") ~ .col:nth-child(7):contains(${status})`,
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
/**
 * Check if the nth row contains the given string.
 * Note that 1st row is the header-row.
 * @param {boolean | undefined} viewMode true if in mobile view, false if in desktop, undefined if in both views.
 */
export function nthRowContains(n, string, viewMode) {
    return [
        {
            trigger: `.ticket-screen .orders > .order-row:nth-child(${n}):contains("${string}")`,
            mobile: viewMode,
            run: () => {},
        },
    ];
}
export function contains(string) {
    return [
        {
            trigger: `.ticket-screen .orders:contains("${string}")`,
            run: () => {},
        },
    ];
}
export function noNewTicketButton() {
    return [
        {
            trigger: ".ticket-screen .controls .buttons:nth-child(1):has(.discard)",
            run: () => {},
        },
    ];
}
export function filterIs(name) {
    return [
        {
            trigger: `.ticket-screen .pos-search-bar .filter span:contains("${name}")`,
            run: () => {},
        },
    ];
}
export function invoicePrinted() {
    return [
        {
            trigger: '.ticket-screen .control-button:contains("Reprint Invoice")',
            run: () => {},
        },
    ];
}
export function partnerIs(name) {
    return inLeftSide({
        trigger: `.ticket-screen .set-partner:contains("${name}")`,
        isCheck: true,
    });
}
export function toRefundTextContains(text) {
    return inLeftSide({
        trigger: `.ticket-screen .to-refund-highlight:contains("${text}")`,
        run: () => {},
    });
}
export function refundedNoteContains(text) {
    return inLeftSide({
        trigger: `.ticket-screen .refund-note:contains("${text}")`,
        run: () => {},
    });
}
export function tipContains(amount) {
    return [
        {
            trigger: `.ticket-screen .tip-cell:contains("${amount}")`,
            run: () => {},
        },
    ];
}
export function receiptTotalIs(amount) {
    return [
        {
            trigger: `.receipt-screen .pos-receipt-amount:contains("${amount}")`,
            run: () => {},
        },
    ];
}

export function nthColumnContains(nRow, nCol, string){
    return [
        {
            trigger: `.ticket-screen .order-row:nth-child(${nRow}) > .col:nth-child(${nCol}):contains("${string}")`,
            run: () => {},
        },
    ];
}
