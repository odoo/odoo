import { clickOnSave, registerWebsitePreviewTour, changeOptionInPopover } from "@website/js/tours/tour_utils";

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
            run: () => {}, // This is a check
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
        {
            content: "Click the 'Field' button to add a new field",
            trigger: "[data-container-title='Field'] .o_we_bg_brand_primary",
            run: "click",
        },
        ...changeOptionInPopover("Field", "Type", "[data-action-value='company_name']"),
        {
            content: "Click the 'Field' button to add another field",
            trigger: "[data-container-title='Field'] .o_we_bg_brand_primary",
            run: "click",
        },
        ...changeOptionInPopover("Field", "Type", "[data-action-value='city']"),
        {
            content: "Click the 'Field' button to add another field",
            trigger: ".o_we_bg_brand_primary",
            run: "click",
        },
        {
            content: "Set the label of the new field to 'field_1'",
            trigger: "[data-action-id='setLabelText'] input",
            run: "edit field_1",
        },
        ...clickOnSave(),
        {
            content: "Click the profile button",
            trigger: ".o_user_menu .dropdown-toggle",
            run: "click",
        },
        {
            content: "Click the 'Log out' button",
            trigger: ".dropdown-item[data-menu=logout]",
            run: "click",
        },
        {
            content: "Click the 'Sign in' button",
            trigger: "nav a:contains('Sign in')",
            run: "click",
        },
        {
            content: "Click the 'Dont have an account?' link",
            trigger: ".oe_website_login_container .oe_login_buttons a.btn",
            run: "click",
        },
        {
            content: "Verify that the signup form is displayed",
            trigger: ".o_signup",
            run: () => {}, // This is a check
        },
        ...fillInputField("input#login", "odoo@odoo.com"),
        ...fillInputField("input#name", "odoo_bot"),
        ...fillInputField("input#password", "123456789"),
        ...fillInputField("input#confirm_password", "123456789"),
        ...fillInputField("input[name='company_name']", "odoo Inc Pvt Ltd"),
        ...fillInputField("input[name='city']", "Gandhinagar"),
        ...fillInputField("input[name='field_1']", "this_is_the_text_of_field_1"),
        {
            content: "Submit the signup form",
            trigger: ".s_website_form_send",
            run: "click",
        },
        {
            content: "Navigate to the 'Edit Information' section",
            trigger: "a[href='/my/account']",
            run: "click",
        },
        ...checkField("odoo_bot"),
        ...checkField("odoo@odoo.com"),
        ...checkField("odoo Inc Pvt Ltd"),
        ...checkField("Gandhinagar"),
    ]
);
