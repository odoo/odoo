import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
    insertSnippet,
    changeOption,
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
            content: "Submit the donation form",
            trigger: ":iframe button[name='o_payment_submit_button']",
            run: "click",
        },
        {
            content: "Check if the warning message is displayed",
            trigger: ":iframe .o_donation_payment_form:has(small#warning_message_id)",
        },
        {
            content: "Enter an amount less than the minimum value",
            trigger: ":iframe input#other_amount_value",
            run: "edit 1",
        },
        {
            content:
                "Verify whether the minimum value warning message is displayed while other warning messages remain hidden",
            trigger:
                ":iframe small#warning_min_message_id:contains('The minimum donation amount is $5.'), :iframe .o_donation_payment_form:has(small#warning_message_id.d-none)",
        },
        {
            content: "Click on the first radio button",
            trigger: ":iframe input[name='o_donation_amount']:first-child",
            run: "click",
        },
        {
            content: "Ensure the custom amount value is cleared",
            trigger:
                ":iframe input#other_amount_value:empty, :iframe #warning_min_message_id.d-none",
        },
        {
            content: "Go to home page",
            trigger: ":iframe a[href='/'].nav-link",
            run: "click",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Click on 'Custom Amount' button",
            trigger: ":iframe .s_donation_donate_btn",
            run: "click",
        },
        changeOption("Donation", "we-toggler"),
        changeOption("Donation", '[data-name="slider_opt"]'),
        ...clickOnSave(),
        {
            content: "Click on $10 button",
            trigger: ":iframe .s_donation_btn_description button",
            run: "click",
        },
        {
            content: "Donate using the selected amount",
            trigger: ":iframe .s_donation_donate_btn",
            run: "click",
        },
        {
            content: "Click on the 'Amount to donate' input field",
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
            trigger: ":iframe body:contains(Your payment has been successfully processed.)",
        },
        {
            content: "Verify that the amount displayed is 67",
            trigger: ':iframe span.oe_currency_value:contains("67.00")',
        },
        {
            trigger: ":iframe [name=o_payment_status_alert]:contains(thank you!)",
        },
    ]
);
