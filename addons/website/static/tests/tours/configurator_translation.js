import { localization } from "@web/core/l10n/localization";
import { translatedTermsGlobal } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { clickOnEditAndWaitEditMode } from "@website/js/tours/tour_utils";

function runConfiguratorFlow(industrySearchText, featureOrPageName) {
    return [
        // Configurator first screen
        {
            content: "Click next",
            trigger: "button.o_configurator_show",
            run: "click",
        },
        // Make sure "Back" works
        {
            content: "Use browser's Back",
            trigger: "button.o_change_website_type",
            run() {
                window.history.back();
            },
        },
        {
            content: "Return to description screen",
            trigger: "button.o_configurator_show",
            run: "click",
        },
        // Description screen
        {
            content: "Select a website type",
            trigger: "button.o_change_website_type",
            run: "click",
        },
        {
            content: "Insert a website industry",
            trigger: ".o_configurator_industry input",
            run: "edit ab",
        },
        {
            content: "Select a website industry from the autocomplete",
            trigger: `.o_configurator_industry_wrapper ul li a:contains(${industrySearchText})`,
            run: "click",
        },
        {
            content: "Choose from the objective list",
            trigger: "button.o_change_website_purpose",
            run: "click",
        },
        // Palette screen
        {
            content: "Choose a palette card",
            trigger: ".palette_card",
            run: "click",
        },
        // Features screen
        {
            content: "Select feature or page",
            trigger: `.card:contains(${featureOrPageName})`,
            run: "click",
        },
        {
            id: "build_website",
            content: "Click on build my website",
            trigger: "button.btn-primary",
            run: "click",
        },
        {
            content: "Loader should be shown",
            trigger: ".o_website_loader_container",
            expectUnloadPage: true,
        },
        {
            content: "Wait until the configurator is finished",
            trigger: ":iframe [data-view-xmlid='website.homepage']",
            timeout: 30000,
        },
    ];
}

registry.category("web_tour.tours").add('configurator_translation', {
    url: '/website/configurator',
    steps: () => [
    ...runConfiguratorFlow("in fr", "Parseltongue_privacy"),
    {
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

registry.category("web_tour.tours").add("configurator_page_creation", {
    url: "/website/configurator",
    steps: () => [
        ...runConfiguratorFlow("abbey", "Pricing"),
        // Verify configurator page templates exist in landing pages category.
        {
            content: "Open create content menu",
            trigger: ".o_new_content_container button",
            run: "click",
        },
        {
            content: "Create a new page",
            trigger: "button[title='New Page']",
            run: "click",
        },
        {
            content: "Click on landing pages category",
            trigger: "[data-id='landing']",
            run: "click",
        },
        {
            content: "Check if configurator pages exist",
            trigger: "[data-id='landing'] .o_page_template[data-configurator-page]",
        },
        {
            content: "Configurator pages should appear at the start of the landing category",
            trigger: "[data-id='landing'] .row > :first-child .o_page_template:first-of-type[data-configurator-page]",
        },
        {
            content: "Exit dialog",
            trigger: ".modal-header .btn-close",
            run: "click",
        },
    ],
});
