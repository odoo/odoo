import { inLeftSide } from "@point_of_sale/../tests/tours/utils/common";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";

export function waitForLoading() {
    return [
        {
            content: "waiting for loading to finish",
            trigger: "body:not(:has(.loader))",
            run: function () {},
        },
    ];
}

export function addProductToOrder(product_name) {
    return [
        {
            content: "buy " + product_name,
            trigger: '.product-list .product-name:contains("' + product_name + '")',
        },
        ...inLeftSide(Order.hasLine({ productName: product_name })),
    ];
}

export function setFiscalPositionOnOrder(fp_name) {
    return [
        ProductScreen.clickReview(),
        ...ProductScreen.controlButtonMore(),
        {
            content: "set fiscal position",
            trigger: ".modal-body .control-buttons button.o_fiscal_position_button",
        },
        {
            content: "choose fiscal position " + fp_name + " to add to the order",
            trigger: `.selection-item:contains("${fp_name}")`,
            in_modal: true,
        },
        ...ProductScreen.controlButtonMore(),
        {
            content: "the fiscal position " + fp_name + " has been set to the order",
            trigger: `.modal-body .control-buttons button.o_fiscal_position_button:contains("${fp_name}")`,
            run: function () {},
        },
        {
            ...Dialog.cancel(),
        },
        {
            content: "go back to the products",
            trigger: ".floor-button",
            mobile: true,
        },
    ];
}

export function selectedPaymentHas(name, val) {
    return [
        {
            content: `selected payment is ${name} and has ${val}`,
            trigger: `.paymentlines .paymentline.selected .payment-name:contains("${name}")`,
            extra_trigger: `.paymentlines .paymentline.selected .payment-name:contains("${name}") ~ .payment-amount:contains("${val}")`,
            run: function () {},
        },
    ];
}

export function selectedOrderlineHas({ product, price = null, quantity = null }) {
    return inLeftSide(
        Order.hasLine({ productName: product, quantity, price, withClass: ".selected" })
    );
}

export function gotoPaymentScreenAndSelectPaymentMethod() {
    return [
        {
            content: "go to payment screen",
            trigger: ".button.pay-order-button",
            mobile: false,
        },
        {
            content: "go to payment screen",
            trigger: ".btn-switchpane:contains('Pay')",
            mobile: true,
        },
        {
            content: "pay with cash",
            trigger: '.paymentmethod:contains("Cash")',
        },
    ];
}

export function finishOrder() {
    return [
        {
            content: "validate the order",
            trigger: ".payment-screen .button.next.highlight:visible",
            mobile: false,
        },
        {
            content: "validate the order",
            trigger: ".payment-screen .btn-switchpane:contains('Validate')",
            mobile: true,
        },
        {
            content: "verify that the order has been successfully sent to the backend",
            trigger: ".js_connected:visible",
            isCheck: true,
        },
        {
            content: "click Next Order",
            trigger: ".receipt-screen .button.next.highlight:visible",
            mobile: false,
        },
        {
            content: "Click Next Order",
            trigger: ".receipt-screen .btn-switchpane.validation-button.highlight[name='done']",
            mobile: true,
        },
        {
            content: "check if we left the receipt screen",
            trigger: ".pos-content div:not(:has(.receipt-screen))",
            run: function () {},
        },
    ];
}

export function verifyPaymentRemaining(val) {
    return [
        {
            content: "verify remaining",
            trigger: `.payment-status-remaining .amount:contains("${val}")`,
            run: function () {},
        },
    ];
}

export function verifyPaymentChange(val) {
    return [
        {
            content: "verify change",
            trigger: `.payment-status-change .amount:contains("${val}")`,
            run: function () {},
        },
    ];
}

export function payWithBank() {
    return [
        {
            content: "pay with bank",
            trigger: '.paymentmethod:contains("Bank")',
        },
    ];
}
