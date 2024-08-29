odoo.define("website_payment.tour.donation_snippet_edition", function (require) {
    "use strict";

    const tour = require("web_tour.tour");
    const wTourUtils = require("website.tour_utils");

    tour.register("donation_snippet_edition", {
        test: true,
        url: "/?enable_editor=1",
    }, [
        wTourUtils.dragNDrop({
            id: "s_donation",
            name: "Donation"
        }),
        ...wTourUtils.clickOnSave(),
        // -- Testing the minimum amount --
        {
            content: "Enter a negative custom amount, testing the minimum amount",
            trigger: "#s_donation_amount_input",
            run: "text -5",
        },
        {
            content: "Donate with custom amount set",
            trigger: ".s_donation_donate_btn",
        },
        {
            content: "Check if alert-danger element exists",
            trigger: "p.alert-danger",
        },
        // -- End of testing the minimum amount --
        {
            content: "Enter a custom amount",
            trigger: "#s_donation_amount_input",
            run: "text 55",
        },
        {
            content: "Donate with custom amount set",
            trigger: ".s_donation_donate_btn",
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
            trigger: "input#other_amount_value",
            run: "text 67",
        },
        {
            content: "Select the custom amount radio button",
            trigger: "input#other_amount",
        },
        {
            content: "Submit the donation form",
            trigger: "button[name='o_payment_submit_button']",
        },
        {
            content: "Verify that the amount displayed is 67",
            trigger: 'span.oe_currency_value:contains("67.00")',
            run: () => {}, // This is a check
            timeout: 10000  // Make sure the payment process animation is finished
        },
    ]);
});
