import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import { isSyncStatusConnected } from "@point_of_sale/../tests/pos/tours/utils/chrome_util";

export function nbOrdersIs(nb) {
    return [
        {
            trigger: `.ticket-screen`,
            run: () => {
                const orders = document.querySelectorAll(".ticket-screen .order-row");
                if (orders.length !== nb) {
                    throw new Error(`Expected ${nb} orders, but found ${orders.length}`);
                }
            },
        },
    ];
}
export function clickDiscard() {
    return {
        content: "go back",
        trigger: ".ticket-screen button.discard",
        run: "click",
    };
}
export function selectOrder(orderName) {
    return [
        {
            trigger: `.ticket-screen .order-row:contains("${orderName}")`,
            run: "click",
        },
    ];
}
export function selectOrderByPrice(price) {
    return [
        {
            trigger: `.ticket-screen .order-row:contains("${price}")`,
            run: "click",
        },
        {
            trigger: `.ticket-screen .order-row.active:contains("${price}")`,
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
            isActive: ["mobile"],
            trigger: `.ticket-screen .order-row > div:contains("${orderName}")`,
            run: "click",
        },
        {
            isActive: ["mobile"],
            trigger: `.ticket-screen .order-row:has(div:contains("${orderName}")) .btn-danger`,
            run: "click",
        },
        {
            isActive: ["desktop"],
            trigger: `.ticket-screen .orders .order-row > td:contains("${orderName}") ~ td.text-end button.text-danger`,
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
            run: `edit ${
                field !== "Invoice Number"
                    ? searchWord
                    : "TSJ/" + new Date().getFullYear() + "/" + searchWord
            }`,
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
            trigger: ".ticket-screen .controls .settle-tips",
            run: "click",
        },
        isSyncStatusConnected(),
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
            trigger: ".ticket-screen .btn-primary.pay-order-button",
            run: "click",
        },
    ];
}
export function checkStatus(orderName, status) {
    return [
        {
            isActive: ["desktop"],
            trigger: `.ticket-screen tbody tr > td:contains("${orderName}") ~ td .badge:contains(${status})`,
        },
        {
            isActive: ["mobile"],
            trigger: `.ticket-screen .order-row > div:contains("${orderName}") ~ div .badge:contains(${status})`,
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
            isActive: [viewMode ? "mobile" : "desktop"],
            trigger: `.ticket-screen .orders tbody .order-row:nth-child(${n}):contains("${string}")`,
        },
    ];
}
export function nthRowIsHighlighted(n) {
    return [
        {
            trigger: ".ticket-screen .order-row.highlight",
        },
    ];
}
export function nthRowNotContains(n, string, viewMode) {
    return [
        {
            isActive: [viewMode ? "mobile" : "desktop"],
            trigger: `.ticket-screen .orders tbody .order-row:nth-child(${n}):not(:contains("${string}"))`,
        },
    ];
}
export function contains(string) {
    return [
        {
            trigger: `.ticket-screen .orders:contains("${string}")`,
        },
    ];
}
export function filterIs(name) {
    return [
        {
            trigger: `.ticket-screen .pos-search-bar .filter span:contains("${name}")`,
        },
    ];
}
export function invoicePrinted() {
    return [
        {
            trigger: ProductScreen.controlButtonTrigger("Reprint Invoice"),
        },
    ];
}
export function toRefundTextContains(text) {
    return inLeftSide({
        trigger: `.ticket-screen .to-refund-highlight:contains("${text}")`,
    });
}
export function refundedNoteContains(text) {
    return inLeftSide({
        trigger: `.ticket-screen .refund-note:contains("${text}")`,
    });
}
export function tipContains(amount) {
    return [
        {
            trigger: `.ticket-screen .tip-cell:contains("${amount}")`,
        },
    ];
}
export function receiptTotalIs(amount) {
    return [
        {
            trigger: `.receipt-screen .pos-receipt-amount:contains("${amount}")`,
        },
    ];
}
export function receiptChangeIs(amount) {
    return [
        {
            trigger: `.receipt-screen .receipt-change:contains("${amount}")`,
        },
    ];
}
export function back() {
    return {
        isActive: ["mobile"],
        trigger: ".back-button",
        run: "click",
    };
}
