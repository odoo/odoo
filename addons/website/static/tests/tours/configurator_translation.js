import { localization } from "@web/core/l10n/localization";
import { translatedTerms } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { clickOnEditAndWaitEditMode } from "@website/js/tours/tour_utils";
import * as tourUtils from '@website/js/tours/tour_utils';

registry.category("web_tour.tours").add('configurator_translation', {
    url: '/website/configurator',
    steps: () => [
    ...tourUtils.websiteConfiguratorDescription("business", "ab", "in fr", "get_leads"),
    tourUtils.websiteConfiguratorPalette("#FFFBF6"),
    {
        content: "Select confidentialité",
        trigger: `.card:contains(Parseltongue_privacy)`,
        run: "click",
    }, {
        content: "Click on build my website",
        trigger: 'button.btn-primary',
        run: "click",
    },
    ...tourUtils.websiteConfiguratorLoadHomePage(),
    {
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
