import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import { inLeftSide } from "@point_of_sale/../tests/tours/utils/common";

export function clickNewTicket() {
    return [{ trigger: ".ticket-screen .highlight", run: "click" }];
}
export function clickDiscard() {
    return [
        {
            content: "go back",
            trigger: ".ticket-screen button.discard",
            mobile: false,
            run: "click",
        },
        { ...ProductScreen.back(), mobile: true },
    ];
}
export function selectOrder(orderName) {
    return [
        {
            trigger: `.ticket-screen .order-row > .col:contains("${orderName}")`,
            run: "click",
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
            run: "click",
        },
    ];
}
export function deleteOrder(orderName) {
    return [
        {
            trigger: `.ticket-screen .order-row > .col:contains("${orderName}")`,
            mobile: true,
            run: "click",
        },
        {
            trigger: `.ticket-screen .order-row:has(.col:contains("${orderName}")) .delete-button`,
            mobile: true,
            run: "click",
        },
        {
            trigger: `.ticket-screen .orders > .order-row > .col:contains("${orderName}") ~ .col[name="delete"]`,
            mobile: false,
            run: "click",
        },
    ];
}
export function selectFilter(name) {
    return [
        {
            trigger: `.pos-search-bar .filter`,
            run: "click",
        },
        {
            trigger: `.pos-search-bar .filter ul`,
            run: () => {},
        },
        {
            trigger: `.pos-search-bar .filter ul li:contains("${name}")`,
            run: "click",
        },
    ];
}
export function search(field, searchWord) {
    return [
        {
            trigger: ".pos-search-bar input",
            run: `edit ${searchWord}`,
        },
        {
            trigger: `.pos-search-bar .search ul li:contains("${field}")`,
            run: "click",
        },
    ];
}
export function settleTips() {
    return [
        {
            trigger: ".ticket-screen .buttons .settle-tips",
            run: "click",
        },
        {
            content: "verify that the order has been successfully sent to the backend",
            trigger: ".js_connected:visible",
            run: function () {},
        },
    ];
}
export function clickControlButton(name) {
    return [
        ProductScreen.clickReview(),
        {
            trigger: `.ticket-screen ${ProductScreen.controlButtonTrigger(name)}`,
            run: "click",
        },
    ];
}
export function confirmRefund() {
    return [
        ProductScreen.clickReview(),
        {
            trigger: ".ticket-screen .button.pay-order-button",
            run: "click",
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
            trigger: ProductScreen.controlButtonTrigger("Reprint Invoice"),
            run: () => {},
        },
    ];
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
