import { localization } from "@web/core/l10n/localization";
import { translatedTermsGlobal } from "@web/core/l10n/translation";
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
        trigger: 'button.o_change_website_type',
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
        trigger: 'button.o_change_website_type',
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
        content: "choose from the objective list",
        trigger: 'button.o_change_website_purpose',
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
        id: "build_website",
        content: "Click on build my website",
        trigger: 'button.btn-primary',
        run: "click",
    }, {
        content: "Loader should be shown",
        trigger: ".o_website_loader_container",
        expectUnloadPage: true,
    }, {
        content: "Wait until the configurator is finished",
        trigger: ":iframe [data-view-xmlid='website.homepage']",
        timeout: 30000,
    }, {
        content: "Check if the current interface language is active and monkey patch terms",
        trigger: "body",
        run() {
            if (localization.code !== "pa_GB") {
                throw new Error("The user language is not the correct one");
            } else {
                translatedTermsGlobal["Save"] = "Save_Parseltongue";
            }
        }
    },
    ...clickOnEditAndWaitEditMode(),
    {
        // Check the content of the save button to make sure the website is in
        // Parseltongue. (The editor should be in the website's default language,
        // which should be parseltongue in this test.)
        content: "exit edit mode",
        trigger: ".o-snippets-top-actions button.btn-success:contains('Save_Parseltongue')",
        run: "click",
    }, {
         content: "wait for editor to be closed",
         trigger: ':iframe #wrapwrap:not(.odoo-editor-editable)',
    }
]});
