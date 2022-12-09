/** @odoo-module */

import Tour from "web_tour.tour";

function add_product_to_order(product_name) {
    return [
        {
            content: "buy " + product_name,
            trigger: '.product-list .product-name:contains("' + product_name + '")',
        },
        {
            content: "the " + product_name + " have been added to the order",
            trigger: '.order .product-name:contains("' + product_name + '")',
            run: function () {},
        },
    ];
}

function set_fiscal_position_on_order(fp_name) {
    return [
        {
            content: "set fiscal position",
            trigger: ".control-button.o_fiscal_position_button",
        },
        {
            content: "choose fiscal position " + fp_name + " to add to the order",
            trigger: '.popups .popup .selection .selection-item:contains("' + fp_name + '")',
        },
        {
            content: "the fiscal position " + fp_name + " has been set to the order",
            trigger: '.control-button.o_fiscal_position_button:contains("' + fp_name + '")',
            run: function () {},
        },
    ];
}

function press_payment_numpad(val) {
    return [
        {
            content: `press ${val} on payment screen numpad`,
            trigger: `.payment-numpad .input-button:contains("${val}"):visible`,
        },
    ];
}

function press_product_numpad(val) {
    return [
        {
            content: `press ${val} on product screen numpad`,
            trigger: `.numpad .input-button:contains("${val}"):visible`,
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
    const result = [];
    if (price !== null) {
        result.push({
            content: `Selected line has product '${product}' and price '${price}'`,
            trigger: `.order-container .orderlines .orderline.selected .product-name:contains("${product}") ~ span.price:contains("${price}")`,
            run: function () {},
        });
    }
    if (quantity !== null) {
        result.push({
            content: `Selected line has product '${product}' and quantity '${quantity}'`,
            trigger: `.order-container .orderlines .orderline.selected .product-name:contains('${product}') ~ .info-list .info em:contains('${quantity}')`,
            run: function () {},
        });
    }
    return result;
}

function verify_order_total(total_str) {
    return [
        {
            content: "order total contains " + total_str,
            trigger: '.order .total .value:contains("' + total_str + '")',
            run: function () {}, // it's a check
        },
    ];
}

function goto_payment_screen_and_select_payment_method() {
    return [
        {
            content: "go to payment screen",
            trigger: ".button.pay",
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
        },
        {
            content: "verify that the order has been successfully sent to the backend",
            trigger: ".js_connected:visible",
            run: function () {},
        },
        {
            content: "click Next Order",
            trigger: ".receipt-screen .button.next.highlight:visible",
        },
        {
            content: "check if we left the receipt screen",
            trigger: ".pos-content .screen:not(:has(.receipt-screen))",
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
    {
        // Leave category displayed by default
        content: "click category switch",
        trigger: ".breadcrumb-home",
    },
];

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
steps = steps.concat(press_payment_numpad("5"));
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
        trigger: '.paymentmethod:contains("Cash")',
    },
]);
steps = steps.concat(selected_payment_has("Cash", "5.2"));
steps = steps.concat(press_payment_numpad("6"));
steps = steps.concat(selected_payment_has("Cash", "6.0"));
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
        content: "open closing the Point of Sale frontend popup",
        trigger: ".header-button",
    },
    {
        content: "close the Point of Sale frontend",
        trigger: ".close-pos-popup .button:contains('Discard')",
        run: function () {}, //it's a check,
    },
]);

Tour.register("pos_basic_order", { test: true, url: "/pos/ui" }, steps);
