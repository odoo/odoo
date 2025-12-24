import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import { inLeftSide } from "@point_of_sale/../tests/tours/utils/common";
import { isSyncStatusConnected } from "@point_of_sale/../tests/tours/utils/chrome_util";

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
            trigger: `.ticket-screen .order-row > .col:contains("${orderName}")`,
            run: "click",
        },
    ];
}
export function selectOrderByPrice(price) {
    return [
        {
            trigger: `.ticket-screen .order-row > .col:contains("${price}")`,
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
            isActive: ["mobile"],
            trigger: `.ticket-screen .order-row > .col:contains("${orderName}")`,
            run: "click",
        },
        {
            isActive: ["mobile"],
            trigger: `.ticket-screen .order-row:has(.col:contains("${orderName}")) .delete-button`,
            run: "click",
        },
        {
            isActive: ["desktop"],
            trigger: `.ticket-screen .orders > .order-row > .col:contains("${orderName}") ~ .col[name="delete"]`,
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
            trigger: `.ticket-screen .order-row > .col:contains("${orderName}") ~ .col:nth-child(7):contains(${status})`,
        },
        {
            isActive: ["mobile"],
            trigger: `.ticket-screen .order-row > .col:contains("${orderName}") ~ .col:nth-child(2):contains(${status})`,
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
            trigger: `.ticket-screen .orders > .order-row:nth-child(${n}):contains("${string}")`,
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
export function noNewTicketButton() {
    return [
        {
            trigger: ".ticket-screen .controls .buttons:nth-child(1):has(.discard)",
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
export function noLinesToRefund() {
    return inLeftSide({
        content: "No lines are marked for to refund or refunding",
        trigger: ".ticket-screen:not(:has(.to-refund-highlight))",
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

export function nthColumnContains(nRow, nCol, string) {
    return [
        {
            trigger: `.ticket-screen .order-row:nth-last-child(${nRow}) > .col:nth-child(${nCol}):contains("${string}")`,
        },
    ];
}

export function noOrderIsThere() {
    return {
        content: "No orders should be visible on the Ticket Screen",
        trigger: ".ticket-screen:not(:has(.order-row))",
    };
}
