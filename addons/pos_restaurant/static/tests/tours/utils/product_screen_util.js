import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as TextInputPopup from "@point_of_sale/../tests/generic_helpers/text_input_popup_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";

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
export function guestNumberIs(num) {
    return [
        ...ProductScreen.clickControlButtonMore(),
        {
            content: `guest number is ${num}`,
            trigger: ProductScreen.controlButtonTrigger("Guests") + `:contains(${num})`,
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
export function clickCourseButton() {
    return [
        {
            content: "click course button",
            trigger: `.course-btn`,
            run: "click",
        },
    ];
}
export function selectCourseLine(name) {
    return [
        {
            content: `select course ${name}`,
            trigger: `.order-course-name:contains(${name})`,
            run: "click",
        },
    ];
}
export function fireCourseButton() {
    return [
        {
            content: "fire course button",
            trigger: `.actionpad .fire-btn`,
            run: "click",
        },
    ];
}
export function fireCourseButtonHighlighted(courseName) {
    return [
        {
            content: "fire course button highlighted",
            trigger: `.actionpad .fire-btn.btn-primary:contains('Fire ${courseName}')`,
        },
    ];
}
export function payButtonNotHighlighted() {
    return [
        {
            content: "pay button not highlighted",
            trigger:
                ".actionpad .pay-order-button:not('.highlight'):not('.btn-primary'):contains('Payment')",
        },
    ];
}
export function setTab(name) {
    return [
        {
            content: `set tab to ${name}`,
            trigger: `.product-screen .new-tab`,
            run: "click",
        },
        TextInputPopup.inputText(name),
        Dialog.confirm(),
    ];
}

export function releaseTable() {
    return [
        {
            content: "release table",
            trigger: ".product-screen .leftpane .unbook-table",
            run: "click",
        },
    ];
}

export function addCourse() {
    return {
        content: `click Course button`,
        trigger: ProductScreen.controlButtonTrigger("Course"),
        run: "click",
    };
}

export function transferCourseTo(destCourse) {
    return [
        ...ProductScreen.clickControlButton("Transfer course"),
        {
            content: `click ${destCourse} from available courses`,
            trigger: `.modal-body button:contains(${destCourse})`,
            run: "click",
        },
    ];
}

export function discardOrderWarningDialog() {
    return [
        {
            trigger: `.modal-dialog:contains("It seems that the order has not been sent. Would you like to send it to preparation?")`,
        },
        Dialog.discard(),
    ];
}

export function confirmOrderWarningDialog() {
    return [
        {
            trigger: `.modal-dialog:contains("It seems that the order has not been sent. Would you like to send it to preparation?")`,
        },
        Dialog.confirm(),
    ];
}
