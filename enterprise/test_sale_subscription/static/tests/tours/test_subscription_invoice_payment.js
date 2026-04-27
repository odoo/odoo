/** @odoo-module **/

import { registry } from "@web/core/registry";

const tourRegistry = registry.category("web_tour.tours");

function selectDemoPaymentProvider(methodTrigger) {
    return [
        {
            content: "check payment method",
            trigger: methodTrigger,
        },
        {
            content: "select Demo payment provider",
            trigger: "input[data-provider-code=demo]",
            run: "click",
        },
    ];
}

const clickPayNowButton = {
    content: "click Pay Now button",
    trigger: "a.btn-primary:contains(Pay Now)",
    run: "click",
};

const selectNewPaymentMethod =
    selectDemoPaymentProvider("#o_payment_methods:contains(Choose a payment method)");

const selectSavedPaymentMethod =
    selectDemoPaymentProvider("#o_payment_tokens_heading:contains(Your payment methods)");

const confirmPayment = [
    {
        content: "click Pay button",
        trigger: "button[name=o_payment_submit_button]",
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: "wait for payment processing confirmation",
        trigger: "#o_payment_status_message:contains(payment has been successfully processed)",
    },
];

tourRegistry.add("test_subscription_invoice_payment", {
    steps: () => [clickPayNowButton, ...selectNewPaymentMethod, ...confirmPayment],
});

tourRegistry.add("test_subscription_invoice_tokenize", {
    steps: () => [
        clickPayNowButton,
        ...selectNewPaymentMethod,
        {
            content: "automate Payment using new token",
            trigger: "input[name=o_payment_tokenize_checkbox]",
            run: "click",
        },
        ...confirmPayment,
    ],
});

tourRegistry.add("test_subscription_invoice_automate", {
    steps: () => [
        clickPayNowButton,
        ...selectNewPaymentMethod,
        {
            content: "automate Payment using new token",
            trigger: "input[name=o_payment_automate_payments_new_token]",
            run: "click",
        },
        ...confirmPayment,
    ],
});

tourRegistry.add("test_subscription_invoice_tokenized_payment", {
    steps: () => [
        clickPayNowButton,
        ...selectSavedPaymentMethod,
        ...confirmPayment,
    ],
});

tourRegistry.add("test_subscription_invoice_tokenized_automate", {
    steps: () => [
        clickPayNowButton,
        ...selectSavedPaymentMethod,
        {
            content: "automate payment using saved token",
            trigger: "input[name=o_payment_automate_payments_saved_token]",
            run: "click",
        },
        ...confirmPayment,
    ],
});
