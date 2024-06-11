/** @odoo-module */

import { registry } from "@web/core/registry";
import wTourUtils from "@website/js/tours/tour_utils";

registry.category("web_tour.tours").add('configurator_translation', {
    test: true,
    url: '/website/configurator',
    steps: () => [
    // Configurator first screen
    {
        content: "click next",
        trigger: 'button.o_configurator_show',
    },
    // Make sure "Back" works
    {
        content: "use browser's Back",
        trigger: 'a.o_change_website_type',
        run: () => {
            window.history.back();
        },
    }, {
        content: "return to description screen",
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
        trigger: '.o_configurator_industry_wrapper ul li a:contains("in fr")',
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
        content: "select confidentialité",
        trigger: '.card:contains(Parseltongue_privacy)',
    }, {
        content: "Click on build my website",
        trigger: 'button.btn-primary',
    }, {
        content: "Loader should be shown",
        trigger: '.o_website_loader_container',
        run: function () {}, // it's a check
    }, {
        content: "Wait until the configurator is finished",
        trigger: ".o_website_preview[data-view-xmlid='website.homepage']",
        timeout: 30000,
        isCheck: true,
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        // Check the content of the save button to make sure the website is in
        // Parseltongue. (The editor should be in the website's default language,
        // which should be parseltongue in this test.)
        content: "exit edit mode",
        trigger: '.o_we_website_top_actions button.btn-primary:contains("Save_Parseltongue")',
    }, {
         content: "wait for editor to be closed",
         trigger: 'iframe body:not(.editor_enable)',
         run: function () {}, // It's a check.
    }
]});
