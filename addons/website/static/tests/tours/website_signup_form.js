import {
    clickOnSave,
    registerWebsitePreviewTour,
    changeOptionInPopover,
} from "@website/js/tours/tour_utils";

function addNewField() {
    return [
        {
            content: "Click the 'Field' button to add a new field",
            trigger: "div[data-container-title='Field'] button.btn-success",
            run: "click",
        },
        {
            content: "Wait until the new field type options are displayed",
            trigger: "[data-label='Type'] button:contains('text')",
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
function checkField(value) {
    return [
        {
            content: `Verify if the field is correctly set to '${value}'`,
            trigger: `input[value='${value}']`,
        },
    ];
}

registerWebsitePreviewTour(
    "website_signup_form_add_custom_field",
    {
        url: "/web/signup",
        edition: true,
    },
    () => [
        {
            content: "Select the 'Confirm Password' field to proceed",
            trigger: ":iframe input#confirm_password",
            run: "click",
        },
        ...addNewField(),
        ...changeOptionInPopover("Field", "Type", "[data-action-value='zip']"),
        ...addNewField(),
        ...changeOptionInPopover("Field", "Type", "[data-action-value='city']"),
        ...addNewField(),
        {
            content: "Set the label of the new field to 'field_1'",
            trigger: "[data-action-id='setLabelText'] input",
            run: "edit field_1",
        },
        ...clickOnSave(),
    ]
);

registerWebsitePreviewTour(
    "website_signup_custom_form_submit",
    {
        url: "/web/login",
    },
    () => [
        {
            content: "Click the 'Dont have an account?' link",
            trigger: ".oe_login_buttons a:contains('Don't have an account?')",
            expectUnloadPage: true,
            run: "click",
        },
        {
            content: "Verify that the signup form is displayed",
            trigger: ".o_signup",
        },
        ...fillInputField("input#login", "odoo@odoo.com"),
        ...fillInputField("input#name", "odoo_bot"),
        ...fillInputField("input#password", "123456789"),
        ...fillInputField("input#confirm_password", "123456789"),
        ...fillInputField("input[name='zip']", "380006"),
        ...fillInputField("input[name='city']", "Gandhinagar"),
        ...fillInputField("input[name='field_1']", "this_is_the_text_of_field_1"),
        {
            content: "Submit the signup form",
            trigger: ".s_website_form_send",
            expectUnloadPage: true,
            run: "click",
        },
        {
            content: "Navigate to the 'Edit Information' section",
            trigger: "a[href='/my/account']",
            expectUnloadPage: true,
            run: "click",
        },
        ...checkField("odoo_bot"),
        ...checkField("odoo@odoo.com"),
        ...checkField("380006"),
        ...checkField("Gandhinagar"),
    ]
);
