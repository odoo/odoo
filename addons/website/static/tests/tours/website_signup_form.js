import { post } from "@web/core/network/http_service";
import { redirect } from "@web/core/utils/urls";
import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const fieldsAreaSelector = ":iframe #oe_structure_signup_fields";
const lastFieldSelector = `${fieldsAreaSelector} .s_website_form_field:last-child`;

const selectSignupForm = () => [
    {
        content: "Click on the signup form to display its options",
        trigger: ":iframe form.oe_signup_form label[for='login']",
        run: "click",
    },
    {
        content: "Check that no field of the form is selected",
        trigger: ".o_customize_tab:not(:has([data-container-title='Field']))",
    },
    {
        content: 'Click on "+ Field" in the "Sign Up Fields" options',
        trigger: "[data-container-title='Sign Up Fields'] button:contains('+ Field')",
        run: "click",
    },
    {
        content: "Check that the field is added at the end of the form",
        trigger: `${lastFieldSelector}:contains('Custom Text')`,
    },
];
const addCustomField = (label) => [
    ...selectSignupForm(),
    {
        content: `Rename the added field "${label}"`,
        trigger: `${lastFieldSelector} .s_website_form_label_content`,
        run: `editor ${label}`,
    },
    {
        content: `Check that the name of the added field follows its "${label}" label`,
        trigger: `${lastFieldSelector} .s_website_form_input[name='${label}']`,
    },
];
const addExistingField = (fieldName, label) => [
    ...selectSignupForm(),
    {
        content: "Open the type selector of the added field",
        trigger: "[data-container-title='Field'] button:contains('Text')",
        run: "click",
    },
    {
        content: `Select the existing "${label}" field as type`,
        trigger: `.o_popover [data-action-id='existingField'][data-action-value='${fieldName}']`,
        run: "click",
    },
    {
        content: `Check that the added field is the existing "${label}" one`,
        trigger: `${lastFieldSelector} .s_website_form_input[name='${fieldName}']`,
    },
];
const checkFieldIsSaved = (name) => ({
    content: `Check that the "${name}" field is still in the form once saved`,
    trigger: `${fieldsAreaSelector} .s_website_form_input[name='${name}']`,
});
const fillField = (name, value) => ({
    content: `Fill "${value}" in the "${name}" field`,
    trigger: `input[name='${name}']`,
    run: `edit ${value}`,
});

registerWebsitePreviewTour("website_signup_form", {}, () => [
    ...clickOnEditAndWaitEditMode(),
    ...addCustomField("Notes"),
    ...addCustomField("Comments"),
    ...addExistingField("city", "City"),
    ...addExistingField("phone", "Phone"),
    ...clickOnSave(),
    checkFieldIsSaved("Notes"),
    checkFieldIsSaved("Comments"),
    checkFieldIsSaved("city"),
    checkFieldIsSaved("phone"),
    {
        content: "Log out to reach the signup form as a visitor",
        trigger: `${fieldsAreaSelector} .s_website_form_input[name='phone']`,
        async run() {
            const url = await post(
                "/web/session/logout?redirect=/web/signup",
                { csrf_token: odoo.csrf_token },
                "url"
            );
            redirect(url);
        },
        expectUnloadPage: true,
    },
    fillField("name", "Test Signup"),
    fillField("login", "test.submit@example.com"),
    fillField("password", "Test.Signup1"),
    fillField("confirm_password", "Test.Signup1"),
    fillField("Notes", "yes please"),
    fillField("Comments", "From the editor"),
    fillField("city", "Grand-Rosière"),
    fillField("phone", "+32 495 00 00 00"),
    {
        content: 'Click on "Sign up"',
        trigger: ".oe_login_buttons button[type='submit']",
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: "Check that the signup form is gone: the user is signed up",
        trigger: "body:not(:has(form.oe_signup_form))",
    },
]);
