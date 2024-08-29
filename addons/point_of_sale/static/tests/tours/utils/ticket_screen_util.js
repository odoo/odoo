import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import { isSyncStatusConnected } from "@point_of_sale/../tests/tours/utils/chrome_util";
import { Kanban, List } from "./generic_components/web_view_utils";

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
            isActive: ["desktop"],
            ...List.clickRow(orderName),
        },
        {
            isActive: ["mobile"],
            ...Kanban.click(orderName),
        },
    ];
}
export function loadSelectedOrder() {
    return [
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
        {
            trigger: `.ticket-screen ${ProductScreen.controlButtonTrigger(name)}`,
            run: "click",
        },
    ];
}
export function confirmRefund() {
    return [
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
            trigger: List.rowTrigger(orderName) + `:contains("${status}")`,
        },
        {
            isActive: ["mobile"],
            trigger: Kanban.trigger(orderName) + `:contains("${status}")`,
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
    return {
        trigger: `.ticket-screen .to-refund-highlight:contains("${text}")`,
    };
}
export function refundedNoteContains(text) {
    return {
        trigger: `.ticket-screen .refund-note:contains("${text}")`,
    };
}
export function receiptTotalIs(amount) {
    return [
        {
            trigger: `.receipt-screen .pos-receipt-amount:contains("${amount}")`,
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
