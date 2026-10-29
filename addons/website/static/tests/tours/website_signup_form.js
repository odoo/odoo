import { post } from "@web/core/network/http_service";
import { redirect } from "@web/core/utils/urls";
import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
    unfoldOptionsGroup,
} from "@website/js/tours/tour_utils";

const formSelector = ":iframe form.oe_signup_form";
// The added fields are inserted before the submit button, the last element.
const lastFieldSelector = `${formSelector} .s_website_form_rows > .s_website_form_field:nth-last-child(2)`;
const passwordsSwappedSelector = `${formSelector} .s_website_form_field:has(input[name='confirm_password']) + .s_website_form_field input[name='password']`;
const formOptionsSelector = "[data-container-title='Sign Up Form']";
const fieldOptionsSelector = "[data-container-title='Field']";

const selectForm = () => [
    {
        content: "Click on the email field of the signup form",
        trigger: `${formSelector} label[for='login']`,
        run: "click",
    },
    {
        content: "Select the signup form only",
        trigger: `${formOptionsSelector} [title='Select only this block']`,
        run: "click",
    },
    {
        content: "Check that no field of the form is selected",
        trigger: ".o_customize_tab:not(:has([data-container-title='Field']))",
    },
];
const addField = () => [
    ...selectForm(),
    {
        content: 'Click on "+ Field" in the "Sign Up Form" options',
        trigger: `${formOptionsSelector} button:contains('+ Field')`,
        run: "click",
    },
    {
        content: "Check that the field is added at the end of the form",
        trigger: `${lastFieldSelector}:contains('Custom Text')`,
    },
];
const addCustomField = (label) => [
    ...addField(),
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
    ...addField(),
    {
        content: "Open the type selector of the added field",
        trigger: `${fieldOptionsSelector} button:contains('Text')`,
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
const selectLabelsPosition = (position) => ({
    content: `Put the labels of the fields "${position}"`,
    trigger: `${formOptionsSelector} [data-label='Labels Position'] button[data-action-value='${position}']`,
    run: "click",
});
const checkFieldIsSaved = (name) => ({
    content: `Check that the "${name}" field is still in the form once saved`,
    trigger: `${formSelector} .s_website_form_input[name='${name}']`,
});
const fillField = (name, value) => ({
    content: `Fill "${value}" in the "${name}" field`,
    trigger: `input[name='${name}']`,
    run: `edit ${value}`,
});

registerWebsitePreviewTour("website_signup_form", {}, () => [
    ...clickOnEditAndWaitEditMode(),
    {
        content: "Click on the password field",
        trigger: `${formSelector} label[for='password']`,
        run: "click",
    },
    {
        content: "Check that the password field can neither be hidden nor be given a value",
        trigger: `${fieldOptionsSelector}:has([data-label='Placeholder']):not(:has([data-label='Visibility Rule'], [data-label='Default Value']))`,
    },
    ...unfoldOptionsGroup("Sign Up Form"),
    {
        content: "Check that the signup form keeps signing the user up on success",
        trigger: `${formOptionsSelector}:has([data-label='Labels Position']):not(:has([data-label='On Success']))`,
    },
    selectLabelsPosition("left"),
    {
        content: "Check that the standard fields are rendered again as they were",
        trigger: `${formSelector}:has(.s_col_no_resize input[type='email'][name='login']) .s_col_no_resize .input-group:has(.o_show_password) > input[type='password'][name='confirm_password']`,
    },
    selectLabelsPosition("top"),
    {
        content: "Check that the labels are back on top",
        trigger: `${formSelector} .s_website_form_field:not(:has(.s_col_no_resize)) input[type='password'][name='password']`,
    },
    {
        content: "Click on the confirm password field",
        trigger: `${formSelector} label[for='confirm_password']`,
        run: "click",
    },
    {
        content: "Move the confirm password field up",
        trigger: ".o_overlay_options button[title='Move up']",
        run: "click",
    },
    {
        content: "Check that the confirm password field is above the password one",
        trigger: passwordsSwappedSelector,
    },
    ...selectForm(),
    {
        content: "Check that the signup form can neither be removed nor be duplicated",
        trigger:
            "body:not(:has(.o_overlay_options [title='Remove'], .o_overlay_options [title='Duplicate']))",
    },
    ...addCustomField("Notes"),
    ...addCustomField("Comments"),
    ...addExistingField("city", "City"),
    ...addExistingField("phone", "Phone"),
    ...clickOnSave(),
    {
        content: "Check that the moved field is still in its place once saved",
        trigger: passwordsSwappedSelector,
    },
    checkFieldIsSaved("Notes"),
    checkFieldIsSaved("Comments"),
    checkFieldIsSaved("city"),
    checkFieldIsSaved("phone"),
    {
        content: "Log out to reach the signup form as a visitor",
        trigger: `${formSelector} .s_website_form_input[name='phone']`,
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
    {
        content: "Check that the password policy, if any, applies to the password",
        trigger: "form.oe_signup_form input[name='password']",
        run() {
            const { passwordMinlength } = document.querySelector(
                "[data-for='o_signup_form']"
            ).dataset;
            const fieldEl = this.anchor.closest(".s_website_form_field");
            if (
                passwordMinlength &&
                (this.anchor.getAttribute("minlength") !== passwordMinlength ||
                    !fieldEl.querySelector("owl-component[name='password_meter']"))
            ) {
                throw new Error("The password policy should apply to the password field");
            }
        },
    },
    {
        content: 'Click on "Sign up" without filling in the form',
        trigger: ".oe_login_buttons button[type='submit']",
        run: "click",
    },
    {
        content: "Check that the form is checked as the other form snippets",
        trigger:
            "form.oe_signup_form #s_website_form_result:contains('Please fill in the form correctly.')",
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
