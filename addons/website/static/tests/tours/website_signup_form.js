import { clickOnSave, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

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
            content: "Select the confirm password field to proceed",
            trigger: ":iframe input#confirm_password",
            run: "click",
        },
        {
            content: "Click the `Field` button to add a new field",
            trigger: ".o_we_bg_brand_primary",
            run: "click",
        },
        {
            content: "Open the field type dropdown",
            trigger: "we-select[data-name='type_opt']",
            run: "click",
        },
        {
            content: "Select the company_name from existing field",
            trigger: "we-button[data-existing-field='company_name']",
            run: "click",
        },
        {
            content: "Click the `Field` button to add a new field",
            trigger: ".o_we_bg_brand_primary",
            run: "click",
        },
        {
            content: "Open the field type dropdown",
            trigger: "we-select[data-name='type_opt']",
            run: "click",
        },
        {
            content: "Select the city from existing field",
            trigger: "we-button[data-existing-field='city']",
            run: "click",
        },
        {
            content: "Click the `Field` button to add a new field",
            trigger: ".o_we_bg_brand_primary",
            run: "click",
        },
        {
            content: "Set the label of the new field to 'field_1'",
            trigger: "we-input[data-set-label-text] input",
            run: "edit field_1",
        },
        ...clickOnSave(),
        {
            content: "click the profile button",
            trigger: ".o_user_menu .dropdown-toggle",
            run: "click",
        },
        {
            content: "click the Log out button",
            trigger: ".dropdown-item[data-menu=logout]",
            run: "click",
        },
        {
            content: "click the sign-in button",
            trigger: "nav a:contains('Sign in')",
            run: "click",
        },
        {
            content: "click the 'Dont have an account?' button",
            trigger: ".oe_website_login_container p a",
            run: "click",
        },
        {
            content: "Verify signup form is displayed",
            trigger: ".s_website_form_send",
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
