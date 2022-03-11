odoo.define('website.tour.automatic_editor', function (require) {
'use strict';

const tour = require('web_tour.tour');

tour.register('automatic_editor_on_new_website', {
    test: true,
    url: '/',
},
[
    {
        content: "Select the language dropdown",
        trigger: '.js_language_selector .dropdown-toggle'
    },
    {
        content: "click on Add a language",
        trigger: 'a.o_add_language',
    },
    {
        content: "type Parseltongue",
        trigger: 'div[name="lang_ids"] .o_input_dropdown input',
        run: 'text Parseltongue',
    },
    {
        content: 'select Parseltongue',
        trigger: 'div[name="lang_ids"] .o_input_dropdown input',
        extra_trigger: '.dropdown-item:contains(Parseltongue)',
        run: function () {
            // The dropdown element is outside the action manager, and can therefor not
            // be selected directly by "trigger".
            // That's why we need to simulate the click in JS
            const element = $('.dropdown-item:contains(Parseltongue)');
            if (!element.length) {
                console.error('Lang not found');
            }
            element.click();
        },
    },
    {
        content: "load parseltongue",
        extra_trigger: '.modal div[name="lang_ids"] .badge-pill .o_tag_badge_text:contains(Parseltongue)',
        trigger: '.modal-footer button:first',
    },
    {
        content: "Select the language dropdown",
        trigger: '.js_language_selector .dropdown-toggle',
    },
    {
        content: "Select parseltongue",
        trigger: 'a.js_change_lang[data-url_code=pa_GB]',
    },
    {
        content: "Check that we're on parseltongue and then go to settings",
        trigger: 'html[lang=pa-GB]',
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
        trigger: 'input[name="name"]',
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
        trigger: 'button[data-name="button_choose_theme"]'
    },
    {
        content: "Check that the editor is loaded",
        trigger: 'body.editor_enable',
        timeout: 30000,
        run: () => null, // it's a check
    },
    {
        content: "exit edit mode",
        trigger: '.o_we_website_top_actions button.btn-primary:contains("Save")',
    },
    {
        content: "wait for editor to close",
        trigger: 'body:not(.editor_enable)',
        run: () => null, // It's a check
    }
]);
});
