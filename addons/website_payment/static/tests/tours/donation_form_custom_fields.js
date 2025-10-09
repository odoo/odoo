import { registry } from "@web/core/registry";
import {
    clickOnSave,
    registerWebsitePreviewTour,
    changeOptionInPopover,
} from "@website/js/tours/tour_utils";

function addNewField() {
    return [
        {
            content: "Click the 'Field' button to add a new field",
            trigger: ".o_we_bg_brand_primary",
            run: "click",
        },
    ];
}

function fillInputField(selector, value) {
    return [
        {
            content: `Fill input field with value ${value}`,
            trigger: `${selector}`,
            run: `edit ${value}`,
        },
    ];
}

registerWebsitePreviewTour(
    "donation_form_custom_field_create",
    {
        url: "/donation/pay",
        edition: true,
    },
    () => [
        {
            content: "Select the 'Email' field to proceed",
            trigger: ":iframe #div_email",
            run: "click",
        },
        ...addNewField(),
        ...changeOptionInPopover("Field", "Type", "[data-action-value='partner_address']"),
        ...addNewField(),
        ...changeOptionInPopover("Field", "Type", "[data-action-value='partner_city']"),
        ...addNewField(),
        {
            content: "Set the label of the new field to 'field_1'",
            trigger: "[data-action-id='setLabelText'] input",
            run: "edit field_1",
        },
        ...clickOnSave(),
    ]
);

registry.category("web_tour.tours").add("donation_form_custom_field_submit", {
    url: "/donation/pay",
    steps: () => [
        {
            content: "Verify that the donation form is displayed",
            trigger: ".o_payment_form_field_container",
        },
        ...fillInputField("input#name", "odoo_bot"),
        ...fillInputField("input#email", "odoo_bot@odoo.com"),
        {
            content: "Select the country from the dropdown",
            trigger: "select#country_id",
            run: "selectByLabel India",
        },
        ...fillInputField("input[name='partner_address']", "odoo Inc Pvt Ltd"),
        ...fillInputField("input[name='partner_city']", "Gandhinagar"),
        ...fillInputField("input[name='field_1']", "this_is_the_text_of_field_1"),
        {
            content: "Submit the donation form",
            trigger: "button[name='o_payment_submit_button']",
            run: "click",
            expectUnloadPage: true,
        },
    ],
});
