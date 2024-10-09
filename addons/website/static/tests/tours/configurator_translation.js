/** @odoo-module */

import { localization } from "@web/core/l10n/localization";
import { translatedTerms } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { clickOnEditAndWaitEditMode } from "@website/js/tours/tour_utils";

registry.category("web_tour.tours").add('configurator_translation', {
    url: '/website/configurator',
    steps: () => [
    // Configurator first screen
    {
        content: "click next",
        trigger: 'button.o_configurator_show',
        run: "click",
    },
    // Make sure "Back" works
    {
        content: "use browser's Back",
        trigger: 'a.o_change_website_type',
        run() {
            window.history.back();
        },
    }, {
        content: "return to description screen",
        trigger: 'button.o_configurator_show',
        run: "click",
    },
    // Description screen
    {
        content: "select a website type",
        trigger: 'a.o_change_website_type',
        run: "click",
    }, {
        content: "insert a website industry",
        trigger: '.o_configurator_industry input',
        run: "edit ab",
    }, {
        content: "select a website industry from the autocomplete",
        trigger: '.o_configurator_industry_wrapper ul li a:contains("in fr")',
        run: "click",
    }, {
        content: "select an objective",
        trigger: '.o_configurator_purpose_dd a',
        run: "click",
    }, {
        content: "choose from the objective list",
        trigger: 'a.o_change_website_purpose',
        run: "click",
    },
    // Palette screen
    {
        content: "chose a palette card",
        trigger: '.palette_card',
        run: "click",
    },
    // Features screen
    {
        content: "select confidentialité",
        trigger: '.card:contains(Parseltongue_privacy)',
        run: "click",
    }, {
        content: "Click on build my website",
        trigger: 'button.btn-primary',
        run: "click",
    }, {
        content: "Loader should be shown",
        trigger: '.o_website_loader_container',
    }, {
        content: "Wait until the configurator is finished",
        trigger: ".o_website_preview[data-view-xmlid='website.homepage']",
        timeout: 30000,
    }, {
        content: "Check if the current interface language is active and monkey patch terms",
        trigger: "body",
        run() {
            if (localization.code !== "pa_GB") {
                throw new Error("The user language is not the correct one");
            } else {
                translatedTerms["Save"] = "Save_Parseltongue";
            }
        }
    },
    ...clickOnEditAndWaitEditMode(),
    {
        // Check the content of the save button to make sure the website is in
        // Parseltongue. (The editor should be in the website's default language,
        // which should be parseltongue in this test.)
        content: "exit edit mode",
        trigger: '.o_we_website_top_actions button.btn-primary:contains("Save_Parseltongue")',
        run: "click",
    }, {
         content: "wait for editor to be closed",
         trigger: ':iframe body:not(.editor_enable)',
    }
]});
