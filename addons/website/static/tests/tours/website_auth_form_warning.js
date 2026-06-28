import {
    registerWebsitePreviewTour,
    clickOnSave,
    clickOnEditAndWaitEditMode,
} from "@website/js/tours/tour_utils";

function logoutAndGoToLoginPage() {
    return [
        {
            content: "Open the user menu",
            trigger: ".o_user_menu",
            run: "click",
        },
        {
            content: "Click on logout button",
            trigger: ".dropdown-item[data-menu=logout]",
            expectUnloadPage: true,
            run: "click",
        },
        {
            content: "Wait for the login page to load as a public user",
            trigger: ".oe_login_form",
        },
    ];
}

function checkWarningVisible(formSelector) {
    return [
        {
            content: "Warning message is shown for already logged-in-user",
            trigger: `:iframe ${formSelector} .oe_login_buttons > p.alert-warning`,
        },
        {
            content: "Submit button is disabled",
            trigger: ":iframe .oe_login_buttons > button[type='submit']:disabled",
        },
    ];
}

function checkWarningHidden(formSelector, { inIframe = true } = {}) {
    const prefix = inIframe ? ":iframe " : "";
    return [
        {
            content: "Warning is not shown in edit mode and also for public user",
            trigger: `${prefix}${formSelector}:not(:has(.oe_login_buttons > p.alert-warning))`,
        },
        {
            content: "Submit button is enabled in edit mode and also for public user",
            trigger: `${prefix}.oe_login_buttons > button[type='submit']:not([disabled])`,
        },
    ];
}

registerWebsitePreviewTour("auth_login_warning", {}, () => [
    ...checkWarningVisible(".oe_login_form"),
    ...clickOnEditAndWaitEditMode(),
    ...checkWarningHidden(".oe_login_form"),
    ...clickOnSave(),
    ...logoutAndGoToLoginPage(),
    ...checkWarningHidden(".oe_login_form", { inIframe: false }),
]);

registerWebsitePreviewTour("auth_signup_warning", {}, () => [
    ...checkWarningVisible(".oe_signup_form"),
    ...clickOnEditAndWaitEditMode(),
    ...checkWarningHidden(".oe_signup_form"),
    ...clickOnSave(),
    ...logoutAndGoToLoginPage(),
    {
        content: "Click sign up link",
        trigger: ".oe_login_buttons > a[href^='/web/signup']",
        expectUnloadPage: true,
        run: "click",
    },
    ...checkWarningHidden(".oe_signup_form", { inIframe: false }),
]);
