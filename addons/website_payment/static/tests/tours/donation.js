/** @odoo-module */

import { registry } from "@web/core/registry";
import wTourUtils from '@website/js/tours/tour_utils';

// First part of the tour
wTourUtils.registerWebsitePreviewTour('donation_snippet_edition', {
    test: true,
    url: '/',
    edition: true,
}, () => [
        ...wTourUtils.dragNDrop({
            id: "s_donation",
            name: "Donation"
        }),
        ...wTourUtils.clickOnSave(),
]);

// Second part of the tour
registry.category('web_tour.tours').add('donation_snippet_use', {
    test: true,
    url: '/',
    steps: () => [
        // -- Testing the minimum amount --
        {
            content: "Enter a negative custom amount, testing the minimum amount",
            trigger: "#s_donation_amount_input",
            run: "edit 1",
        },
        {
            content: "Donate with custom amount set",
            trigger: ".s_donation_donate_btn",
            run: "click",
        },
        {
            content: "Check if alert-danger element exists",
            trigger: "p.alert-danger",
        },
        // -- End of testing the minimum amount --
        {
            content: "Enter a custom amount",
            trigger: "#s_donation_amount_input",
            run: "edit 55",
        },
        {
            content: "Donate with custom amount set",
            trigger: ".s_donation_donate_btn",
            run: "click",
        },
        {
            content: "Check if custom amount radio input is selected",
            trigger: "input#other_amount:checked",
            run: () => {}, // This is a check
        },
        {
            content: "Check if custom amount radio input has value 55",
            trigger: 'input#other_amount[value="55.0"]',
            run: () => {}, // This is a check
        },
        {
            content: "Select the amount of 25",
            trigger: "input#amount_1",
            run: "click",
        },
        {
            content: "Verify that amount_1 is checked",
            trigger: "input#amount_1:checked",
            run: () => {}, // This is a check
        },
        {
            content: "Verify that other_amount is not checked",
            trigger: "input#other_amount:not(:checked)",
            run: () => {}, // This is a check
        },
        {
            content: "Change custom amount to 67",
            trigger: "input[name='o_donation_amount'][type='number']",
            run: function(action) {
                const input = action.anchor;
                input.value = "67";
                input.dispatchEvent(new Event("input", { bubbles: true }));
                input.dispatchEvent(new Event("change", { bubbles: true }));
            }
        },
        {
            content: "Select the custom amount radio button",
            trigger: "input#other_amount",
            run: "click",
        },
        {
            content: "Submit the donation form",
            trigger: "button[name='o_payment_submit_button']",
            run: "click",
        },
        {
            content: "Verify that the amount displayed is 67",
            trigger: 'span.oe_currency_value:contains("67.00")',
            run: () => {}, // This is a check
            timeout: 10000  // Make sure the payment process animation is finished
        },
    ],
});
