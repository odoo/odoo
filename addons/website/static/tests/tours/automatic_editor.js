/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour('automatic_editor_on_new_website', {
    test: true,
    edition: true,
    url: '/',
},
() => [
    wTourUtils.goToTheme(),
    {
        content: "click on Add a language",
        trigger: "we-button[data-add-language]",
        run: "click",
    },
    {
        content: "confirm leave editor",
        trigger: ".modal-dialog button.btn-primary",
        run: "click",
    },
    {
        content: "type Parseltongue",
        trigger: 'div[name="lang_ids"] .o_input_dropdown input',
        run: "edit Parseltongue",
    },
    {
        content: 'select Parseltongue',
        trigger: '.dropdown-item:contains(Parseltongue)',
        in_modal: false,
        run: "click",
    },
    {
        content: "load parseltongue",
        extra_trigger: '.modal div[name="lang_ids"] .rounded-pill .o_tag_badge_text:contains(Parseltongue)',
        trigger: '.modal-footer button[name=lang_install]',
        run: "click",
    },
    {
        content: "Select the language dropdown",
        trigger: ':iframe .js_language_selector .dropdown-toggle',
        run: "click",
    },
    {
        content: "Select parseltongue",
        trigger: ':iframe a.js_change_lang[data-url_code=pa_GB]',
        run: "click",
    },
    {
        content: "Check that we're on parseltongue and then go to settings",
        trigger: ':iframe html[lang=pa-GB]',
        run: () => {
            // Now go through the settings for a new website. A frontend_lang
            // cookie was set during previous steps. It should not be used when
            // redirecting to the frontend in the following steps.
            window.location.href = '/web#action=website.action_website_configuration';
        }
    },
    {
        content: "create a new website",
        trigger: 'button[name="action_website_create_new"]',
        run: "click",
    },
    {
        content: "insert website name",
        trigger: 'div[name="name"] input',
        run: "edit Website EN",
    },
    {
        content: "validate the website creation modal",
        trigger: 'button.btn-primary',
        run: "click",
    },
    {
        content: "skip configurator",
        // This trigger targets the skip button, it doesn't have a more
        // explicit class or ID.
        trigger: '.o_configurator_container .container-fluid .btn.btn-link',
        run: "click",
    },
    {
        content: "make hover button appear",
        trigger: '.o_theme_preview',
        run: () => {
            const el = document.querySelector(".o_theme_preview .o_button_area");
            el.style.visibility = "visible";
            el.style.opacity = 1;
        },
    },
    {
        content: "Install a theme",
        trigger: 'button[name="button_choose_theme"]',
        run: "click",
    },
    {
        content: "Check that the homepage is loaded",
        trigger: ".o_website_preview[data-view-xmlid='website.homepage']",
        extra_trigger: ".o_menu_systray .o_user_menu",
        timeout: 30000,
        isCheck: true,
    },
]);
