odoo.define('test_website_modules.tour.configurator_flow', function (require) {
'use strict';

const tour = require('web_tour.tour');
const wTourUtils = require('website.tour_utils');

tour.register('configurator_flow', {
    test: true,
    url: '/web#action=website.action_website_configuration',
},
[
    {
        content: "click on create new website",
        trigger: 'button[name="action_website_create_new"]',
    }, {
        content: "insert website name",
        trigger: '[name="name"] input',
        run: 'text Website Test',
    }, {
        content: "validate the website creation modal",
        trigger: 'button.btn-primary',
    },
    // Configurator first screen
    {
        content: "click next",
        trigger: 'button.o_configurator_show',
    },
    // Description screen
    {
        content: "select a website type",
        trigger: 'a.o_change_website_type',
    }, {
        content: "insert a website industry",
        trigger: '.o_configurator_industry input',
        run: 'text ab',
    }, {
        content: "select a website industry from the autocomplete",
        trigger: '.o_configurator_industry ul li a',
    }, {
        content: "select an objective",
        trigger: '.o_configurator_purpose_dd a',
    }, {
        content: "choose from the objective list",
        trigger: 'a.o_change_website_purpose',
    },
    // Palette screen
    {
        content: "chose a palette card",
        trigger: '.palette_card',
    },
    // Features screen
    {
        content: "select Pricing",
        trigger: '.card:contains("Pricing")',
    }, {
        content: "Events should be selected (module already installed)",
        extra_trigger: '.card.border-success:contains("Pricing")',
        trigger: '.card.card_installed:contains("Events")',
        run: function () {}, // it's a check
    }, {
        content: "Slides should be selected (module already installed)",
        trigger: '.card.card_installed:contains("eLearning")',
        run: function () {}, // it's a check
    }, {
        content: "Success Stories (Blog) and News (Blog) should be selected (module already installed)",
        extra_trigger: '.card.card_installed:contains("Success Stories")',
        trigger: '.card.card_installed:contains("News")',
        run: function () {}, // it's a check
    }, {
        content: "Click on build my website",
        trigger: 'button.btn-primary',
    }, {
        content: "Loader should be shown",
        trigger: '.o_website_loader_container',
        run: function () {}, // it's a check
    }, {
        content: "Wait untill the configurator is finished",
        trigger: '#oe_snippets.o_loaded',
        timeout: 30000,
    },
    ...wTourUtils.clickOnSave(),
    {
        content: "check menu and footer links are correct",
        trigger: 'body:not(.editor_enable)', // edit mode left
        run: function () {
            const $iframe = this.$anchor.find('iframe.o_iframe:not(.o_ignore_in_tour)');
            for (const menu of ['Home', 'Events', 'Courses', 'Pricing', 'News', 'Success Stories', 'Contact us']) {
                if (!$iframe.contents().find(`#top_menu a:contains(${menu})`).length) {
                    console.error(`Missing ${menu} menu. It should have been created by the configurator.`);
                }
            }
            for (const url of ['/', '/event', '/slides', '/pricing', '/blog/', '/blog/', '/contactus']) {
                if (!$iframe.contents().find(`#top_menu a[href^='${url}'`).length) {
                    console.error(`Missing ${url} menu URL. It should have been created by the configurator.`);
                }
            }
            for (const link of ['Privacy Policy', 'Contact us']) {
                if (!$iframe.contents().find(`#footer ul a:contains(${link})`).length) {
                    console.error(`Missing ${link} footer link. It should have been created by the configurator.`);
                }
            }
        },
    },
]);
});
