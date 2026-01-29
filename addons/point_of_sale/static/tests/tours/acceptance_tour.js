/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as Numpad from "@point_of_sale/../tests/tours/helpers/NumpadTourMethods";
import { registry } from "@web/core/registry";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";

function add_product_to_order(product_name) {
    return [
        {
            content: "buy " + product_name,
            trigger: '.product-list .product-name:contains("' + product_name + '")',
        },
        ProductScreen.clickReview(),
        ...Order.hasLine({ productName: product_name }),
        {
            content: "go back to the products",
            trigger: ".floor-button",
            mobile: true,
        },
    ];
}

function set_fiscal_position_on_order(fp_name) {
    return [
        ProductScreen.clickReview(),
        {
            content: "click more button",
            trigger: ".mobile-more-button",
            mobile: true,
        },
        {
            content: "set fiscal position",
            trigger: ".control-button.o_fiscal_position_button",
        },
        {
            content: "choose fiscal position " + fp_name + " to add to the order",
            trigger: '.popups .popup .selection .selection-item:contains("' + fp_name + '")',
        },
        {
            content: "click more button",
            trigger: ".mobile-more-button",
            mobile: true,
        },
        {
            content: "the fiscal position " + fp_name + " has been set to the order",
            trigger: '.control-button.o_fiscal_position_button:contains("' + fp_name + '")',
            run: function () {},
        },
        {
            content: "go back to the products",
            trigger: ".floor-button",
            mobile: true,
        },
    ];
}

function press_payment_numpad(val) {
    return [{ ...Numpad.click(val), mobile: false }];
}

function fillPaymentLineAmountMobile(lineName, keys) {
    return [
        {
            content: "click payment line",
            trigger: `.paymentlines .paymentline .payment-infos:contains("${lineName}")`,
            mobile: true,
        },
        {
            content: `'${keys}' inputed in the number popup`,
            trigger: ".popup .payment-input-number",
            run: `text ${keys}`,
            mobile: true,
        },
        {
            content: "click confirm button",
            trigger: ".popup .footer .confirm",
            mobile: true,
        },
    ];
}

function fillPaymentValue(lineName, val) {
    return [...press_payment_numpad(val), ...fillPaymentLineAmountMobile(lineName, val)];
}

function press_product_numpad(val) {
    return [
        ProductScreen.clickReview(),
        Numpad.click(val),
        {
            content: "go back to the products",
            trigger: ".floor-button",
            mobile: true,
        },
    ];
}

function selected_payment_has(name, val) {
    return [
        {
            content: `selected payment is ${name} and has ${val}`,
            trigger: `.paymentlines .paymentline.selected .payment-name:contains("${name}")`,
            extra_trigger: `.paymentlines .paymentline.selected .payment-name:contains("${name}") ~ .payment-amount:contains("${val}")`,
            run: function () {},
        },
    ];
}

function selected_orderline_has({ product, price = null, quantity = null }) {
    return [
        ProductScreen.clickReview(),
        ...Order.hasLine({ productName: product, quantity, price, withClass: ".selected" }),
        {
            content: "go back to the products",
            trigger: ".floor-button",
            mobile: true,
        },
    ];
}

function verify_order_total(total_str) {
    return [
        ProductScreen.clickReview(),
        Order.hasTotal(total_str),
        {
            content: "go back to the products",
            trigger: ".floor-button",
            mobile: true,
        },
    ];
}

function goto_payment_screen_and_select_payment_method() {
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

function finish_order() {
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
            run: function () {},
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

var steps = [
    {
        content: "waiting for loading to finish",
        trigger: "body:not(:has(.loader))",
        run: function () {},
    },
];
steps = steps.concat(...ProductScreen.clickHomeCategory());
steps = steps.concat(add_product_to_order("Desk Organizer"));
steps = steps.concat(verify_order_total("5.10"));

steps = steps.concat(add_product_to_order("Desk Organizer"));
steps = steps.concat(verify_order_total("10.20"));
steps = steps.concat(goto_payment_screen_and_select_payment_method());

/*  add payment line of only 5.20
        status:
            order-total := 10.20
            total-payment := 11.70
        expect:
            remaining := 0.00
            change := 1.50
    */
steps = steps.concat(fillPaymentValue("Cash", "5"));
steps = steps.concat(selected_payment_has("Cash", "5.0"));
steps = steps.concat([
    {
        content: "verify remaining",
        trigger: '.payment-status-remaining .amount:contains("5.20")',
        run: function () {},
    },
    {
        content: "verify change",
        trigger: '.payment-status-change .amount:contains("0.00")',
        run: function () {},
    },
]);

/*  make additional payment line of 6.50
        status:
            order-total := 10.20
            total-payment := 11.70
        expect:
            remaining := 0.00
            change := 1.50
    */
steps = steps.concat([
    {
        content: "pay with cash",
        trigger: '.paymentmethod:contains("Bank")',
    },
]);
steps = steps.concat(selected_payment_has("Bank", "5.2"));
steps = steps.concat(fillPaymentValue("Bank", "6"));
steps = steps.concat(selected_payment_has("Bank", "6.0"));
steps = steps.concat([
    {
        content: "verify remaining",
        trigger: '.payment-status-remaining .amount:contains("0.00")',
        run: function () {},
    },
    {
        content: "verify change",
        trigger: '.payment-status-change .amount:contains("0.80")',
        run: function () {},
    },
]);

steps = steps.concat(finish_order());

// test opw-672118 orderline subtotal rounding
steps = steps.concat(add_product_to_order("Desk Organizer"));
steps = steps.concat(selected_orderline_has({ product: "Desk Organizer", quantity: "1.0" }));
steps = steps.concat(press_product_numpad("."));
steps = steps.concat(
    selected_orderline_has({ product: "Desk Organizer", quantity: "0.0", price: "0.0" })
);
steps = steps.concat(press_product_numpad("9"));
steps = steps.concat(
    selected_orderline_has({ product: "Desk Organizer", quantity: "0.9", price: "4.59" })
);
steps = steps.concat(press_product_numpad("9"));
steps = steps.concat(
    selected_orderline_has({ product: "Desk Organizer", quantity: "0.99", price: "5.05" })
);
steps = steps.concat(goto_payment_screen_and_select_payment_method());
steps = steps.concat(selected_payment_has("Cash", "5.05"));
steps = steps.concat(finish_order());

// Test fiscal position one2many map (align with backend)
steps = steps.concat(add_product_to_order("Letter Tray"));
steps = steps.concat(selected_orderline_has({ product: "Letter Tray", quantity: "1.0" }));
steps = steps.concat(verify_order_total("5.28"));
steps = steps.concat(set_fiscal_position_on_order("FP-POS-2M"));
steps = steps.concat(verify_order_total("5.52"));

steps = steps.concat([
    {
        content: "open the navbar menu",
        trigger: ".menu-button",
    },
    {
        content: "open closing the Point of Sale frontend popup",
        trigger: ".close-button",
    },
    {
        content: "close the Point of Sale frontend",
        trigger: ".close-pos-popup .button:contains('Discard')",
        run: function () {}, //it's a check,
    },
]);

registry
    .category("web_tour.tours")
    .add("pos_basic_order", { test: true, url: "/pos/ui", steps: () => steps });
