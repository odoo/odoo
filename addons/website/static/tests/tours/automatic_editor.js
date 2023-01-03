odoo.define('website.tour.automatic_editor', function (require) {
'use strict';

const wTourUtils = require("website.tour_utils");

wTourUtils.registerWebsitePreviewTour('automatic_editor_on_new_website', {
    test: true,
    url: '/',
},
[
    {
        content: "Select the language dropdown",
        trigger: 'iframe .js_language_selector .dropdown-toggle'
    },
    {
        content: "click on Add a language",
        trigger: 'iframe a.o_add_language',
    },
    {
        content: "type Parseltongue",
        trigger: 'div[name="lang_ids"] .o_input_dropdown input',
        run: 'text Parseltongue',
    },
    {
        content: 'select Parseltongue',
        trigger: '.dropdown-item:contains(Parseltongue)',
        in_modal: false,
    },
    {
        content: "load parseltongue",
        extra_trigger: '.modal div[name="lang_ids"] .rounded-pill .o_tag_badge_text:contains(Parseltongue)',
        trigger: '.modal-footer button[name=lang_install]',
    },
    {
        content: "Select the language dropdown",
        trigger: 'iframe .js_language_selector .dropdown-toggle',
    },
    {
        content: "Select parseltongue",
        trigger: 'iframe a.js_change_lang[data-url_code=pa_GB]',
        extra_trigger: 'iframe a.js_change_lang .o_lang_flag',
    },
    {
        content: "Check that we're on parseltongue and then go to settings",
        trigger: 'iframe html[lang=pa-GB]',
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
    },
    {
        content: "insert website name",
        trigger: 'div[name="name"] input',
        run: 'text Website EN'
    },
    {
        content: "validate the website creation modal",
        trigger: 'button.btn-primary'
    },
    {
        content: "skip configurator",
        // This trigger targets the skip button, it doesn't have a more
        // explicit class or ID.
        trigger: '.o_configurator_container .container-fluid .btn.btn-link'
    },
    {
        content: "make hover button appear",
        trigger: '.o_theme_preview',
        run: () => {
            $('.o_theme_preview .o_button_area').attr('style', 'visibility: visible; opacity: 1;');
        },
    },
    {
        content: "Install a theme",
        trigger: 'button[name="button_choose_theme"]'
    },
    {
        content: "Check that the editor is loaded",
        trigger: 'iframe body.editor_enable',
        timeout: 30000,
        run: () => null, // it's a check
    },
    {
        content: "exit edit mode",
        trigger: '.o_we_website_top_actions button.btn-primary:contains("Save")',
    },
    {
        content: "wait for editor to close",
        trigger: 'iframe body:not(.editor_enable)',
        run: () => null, // It's a check
    }
]);
});
