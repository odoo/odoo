import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
    insertSnippet,
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
        // -- Testing the minimum amount --
        {
            content: "Enter a negative custom amount, testing the minimum amount",
            trigger: ":iframe #s_donation_amount_input",
            run: "edit 1",
        },
        {
            content: "Donate with custom amount set",
            trigger: ":iframe .s_donation_donate_btn",
            run: "click",
        },
        {
            content: "Check if alert-danger element exists",
            trigger: ":iframe p.alert-danger",
        },
        // -- End of testing the minimum amount --
        {
            content: "Enter a custom amount",
            trigger: ":iframe #s_donation_amount_input",
            run: "edit 55",
        },
        {
            content: "Donate with custom amount set",
            trigger: ":iframe .s_donation_donate_btn",
            run: "click",
        },
        {
            content: "Check if custom amount radio input is selected",
            trigger: ":iframe input#other_amount:checked",
        },
        {
            content: "Check if custom amount radio input has value 55",
            trigger: ':iframe input#other_amount[value="55.0"]',
        },
        {
            content: "Click on custom amount value",
            trigger: ":iframe input#other_amount_value",
            run: "click",
        },
        {
            content: "Select the amount of 25",
            trigger: ":iframe input#amount_1",
            run: "click",
        },
        {
            content: "Verify that amount_1 is checked",
            trigger: ":iframe input#amount_1:checked",
        },
        {
            content: "Verify that other_amount is not checked",
            trigger: ":iframe input#other_amount:not(:checked)",
        },
        {
            content: "Click on the custom amount radio button",
            trigger: ":iframe input#other_amount",
            run: "click",
        },
        {
            content: "Enter an amount less than the minimum value",
            trigger: ":iframe input#other_amount_value",
            run: "edit 1",
        },
        {
            content: "Check warning message is hidden",
            trigger: ":iframe .o_donation_payment_form:has(p#warningMessageId.d-none)",
        },
        {
            content: "Verify the display of a minimum value warning message",
            trigger: ":iframe p#warningMinMessageId:contains('The minimum donation amount is $5')",
        },
        {
            content: "Click on the first radio button",
            trigger: ":iframe input[name='o_donation_amount']:first-child",
            run: "click",
        },
        {
            content: "Ensure the custom amount value is cleared",
            trigger: ":iframe input[name='o_donation_amount']:first-child",
            run: () => {
                const iframe = document.querySelector("iframe").contentDocument;
                const warningEl = iframe.querySelector("#warningMinMessageId");
                const customAmountEl = iframe.querySelector("#other_amount_value");
                if (!warningEl.classList.contains("d-none") || customAmountEl.value !== "") {
                    console.error("Custom amount should be cleared.");
                }
            }
        },
        {
            content: "Click on home page",
            trigger: ":iframe span[data-oe-model='website.menu']",
            run: "click",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Click on custom donation button",
            trigger: ":iframe .s_donation_donate_btn",
            run: "click",
        },
        {
            content: "Click on selection button",
            trigger: "we-customizeblock-option.snippet-option-Donation we-toggler",
            run: "click",
        },
        {
            content: "Change button to slider",
            trigger: "we-button[data-name='slider_opt']",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Select any button after prefilled buttons",
            trigger: ":iframe .s_donation_prefilled_buttons .s_donation_btn_description",
            run: "click",
        },
        {
            content: "Donate using the selected amount",
            trigger: ":iframe .s_donation_donate_btn",
            run: "click",
        },
        {
            content: "Check the custom amount radio button",
            trigger: ":iframe input#other_amount",
        },
        {
            content: "Click on the custom amount radio button",
            trigger: ":iframe input#other_amount_value",
            run: "click",
        },
        {
            content: "Change custom amount to 67",
            trigger: ":iframe input[name='o_donation_amount'][type='number']",
            run: "edit 67",
        },
        {
            content: "Select the custom amount radio button",
            trigger: ":iframe input#other_amount",
            run: "click",
        },
        {
            content: "Submit the donation form",
            trigger: ":iframe button[name='o_payment_submit_button']",
            run: "click",
        },
        {
            content: "Verify that the amount displayed is 67",
            trigger: ':iframe span.oe_currency_value:contains("67.00")',
            timeout: 10000, // Make sure the payment process animation is finished
        },
    ]
);
