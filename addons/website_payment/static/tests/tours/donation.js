import { registry } from "@web/core/registry";
import {
    clickOnSave,
    registerWebsitePreviewTour,
    insertSnippet,
    changeOptionInPopover,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "donation_snippet_edition",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_donation",
            name: "Donation",
            groupName: "Contact & Forms",
        }),
        ...clickOnSave(),
    ]
);

registry.category("web_tour.tours").add("donation_snippet_use", {
    url: "/",
    steps: () => [
        // -- Testing the minimum amount --
        {
            content: "Enter a custom amount smaller than the minimum, testing the minimum amount",
            trigger: "#s_donation_amount_input",
            run: "edit 1",
        },
        {
            content: "Donate with custom amount set",
            trigger: ".s_donation_donate_btn.o_ready_to_donate",
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
            trigger: ".s_donation_donate_btn.o_ready_to_donate",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Check if custom amount radio input is selected",
            trigger: "input#other_amount:checked",
        },
        {
            content: "Check if custom amount radio input has value 55",
            trigger: 'input#other_amount[value="55.0"]',
        },
        {
            content: "Select the amount of 25",
            trigger: "input#amount_1",
            run: "click",
        },
        {
            content: "Verify that amount_1 is checked",
            trigger: "input#amount_1:checked",
        },
        {
            content: "Verify that other_amount is not checked",
            trigger: "input#other_amount:not(:checked)",
        },
        {
            content: "Click on the custom amount radio button",
            trigger: "input#other_amount",
            run: "click",
        },
        {
            content: "Submit the donation form",
            trigger: "button[name='o_payment_submit_button']",
            run: "click",
        },
        {
            content: "Check if the warning message is displayed",
            trigger: ".o_donation_payment_form:has(small#warning_message_id)",
        },
        {
            content: "Enter an amount less than the minimum value",
            trigger: "input#other_amount_value",
            run: "edit 1",
        },
        {
            content: "Verify whether the minimum value warning message is displayed",
            trigger: "small#warning_min_message_id:contains('The minimum donation amount is $5.')",
        },
        {
            content: "Verify other warning messages remain hidden",
            trigger: ".o_donation_payment_form:has(small#warning_message_id.d-none)",
        },
        {
            content: "Click on the first radio button",
            trigger: "input[name='o_donation_amount']:first-child",
            run: "click",
        },
        {
            content: "Ensure the custom amount value is cleared",
            trigger: "input#other_amount_value:empty",
        },
        {
            content: "Ensure no warning message is displayed",
            trigger: ".o_donation_payment_form:has(#warning_min_message_id.d-none)",
        },
    ],
});

registerWebsitePreviewTour(
    "donation_snippet_edition_2",
    {
        url: "/",
        edition: true,
    },
    () => [
        {
            content: "Click on 'Custom Amount' button",
            trigger: ":iframe .s_donation_donate_btn",
            run: "click",
        },
        ...changeOptionInPopover("Donation Button", "Custom Amount", "[data-action-param='slider']"),
        ...clickOnSave(),
    ]
);

registry.category("web_tour.tours").add("donation_snippet_use_2", {
    url: "/",
    steps: () => [
        {
            content: "Click on $10 button",
            trigger: ".s_donation_btn_description button",
            run: "click",
        },
        {
            content: "Donate using the selected amount",
            trigger: ".s_donation_donate_btn.o_ready_to_donate",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Click on the 'Amount to donate' input field",
            trigger: "input#other_amount_value",
            run: "click",
        },
        {
            content: "Change custom amount to 67",
            trigger: "input[name='o_donation_amount'][type='number']",
            run: "edit 67",
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
            expectUnloadPage: true,
        },
        {
            content: "Verify that the amount displayed is 67",
            trigger:
                'body:contains(Your payment has been processed.) span.oe_currency_value:contains("67.00")',
            expectUnloadPage: true,
        },
        {
            trigger: "[name=o_payment_status_alert]:contains(thank you!)",
        },
    ],
});
