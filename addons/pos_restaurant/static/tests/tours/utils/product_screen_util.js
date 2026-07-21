import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";

export function clickOrderButton() {
    return [
        {
            content: "click order button",
            trigger: ".actionpad .submit-order",
            run: "click",
        },
    ];
}
export function orderlinesHaveNoChange() {
    return Order.doesNotHaveLine({ withClass: ".has-change" });
}
export function orderlineIsToOrder(name) {
    return Order.hasLine({
        productName: name,
        withClass: ".orderline.has-change",
    });
}
export function orderlineIsToSkip(name) {
    return Order.hasLine({
        withClass: ".orderline.skip-change",
        productName: name,
    });
}
export function guestNumberIs(num) {
    return [
        ...ProductScreen.clickControlButtonMore(),
        {
            content: `guest number is ${num}`,
            trigger: ProductScreen.controlButtonTrigger("Guests") + `:contains(${num})`,
        },
    ];
}
export function orderBtnIsPresent() {
    return [
        {
            content: "Order button is here",
            trigger: ".actionpad .button.submit-order",
        },
    ];
}
export function OrderButtonNotContain(data) {
    const steps = [
        {
            isActive: ["desktop"],
            content: "check order button not contain data",
            trigger: `.product-screen .submit-order:not(:contains("${data}"))`,
            run: function () {}, // it's a check
        },
    ];
    return steps;
}

export function OrderButtonCategoryQty(category, qty) {
    return [
        {
            isActive: ["desktop"],
            content: "Check quantity for category on order button",
            trigger: `.product-screen .submit-order div:contains("${category}") label:contains("${qty}")`,
        },
        {
            isActive: ["mobile"],
            content: "Check total quantity order button",
            trigger: `.btn-switchpane.pay-button small:contains("${qty}")`,
        },
    ];
}

export function bookOrReleaseTable() {
    return [
        {
            content: "click book or release table button",
            trigger: ".table-booking button",
            run: "click",
        },
    ];
}

export function clickBookTable() {
    return [
        ProductScreen.clickReview(),
        {
            content: "click book table",
            trigger: ".product-screen .book-table",
            run: "click",
        },
    ];
}
