import { localization } from "@web/core/l10n/localization";
import { translatedTerms } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { clickOnEditAndWaitEditMode } from "@website/js/tours/tour_utils";
import { waitFor } from "@odoo/hoot-dom";

registry.category("web_tour.tours").add("configurator_translation", {
    url: "/website/configurator",
    steps: () => [
        // Configurator first screen
        {
            content: "Click next",
            trigger: "button.o_configurator_show",
            run: "click",
        },
        // Make sure "Back" works
        {
            content: "Use browser's Back",
            trigger: "a.o_change_website_type",
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
            trigger: "a.o_change_website_type",
            run: "click",
        },
        {
            content: "Insert a website industry",
            trigger: ".o_configurator_industry input",
            run: "edit ab",
        },
        {
            content: "Select a website industry from the autocomplete",
            trigger: ".o_configurator_industry_wrapper ul li a:contains('in fr')",
            run: "click",
        },
        {
            content: "Select an objective",
            trigger: ".o_configurator_purpose_dd a",
            run: "click",
        },
        {
            content: "Choose from the objective list",
            trigger: "a.o_change_website_purpose",
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
            content: "Select confidentialité",
            trigger: ".card:contains(Parseltongue_privacy)",
            run: "click",
        },
        {
            content: "Click on build my website",
            trigger: "button.btn-primary",
            run: "click",
        },
        {
            content: "Loader should be shown",
            trigger: ".o_website_loader_container",
        },
        {
            content: "Wait until the configurator is finished",
            trigger: ".o_website_preview[data-view-xmlid='website.homepage']",
            timeout: 30000,
        },
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
            // Check the content of the save button to make sure the website is
            // in Parseltongue. (The editor should be in the website's default
            // language, which should be parseltongue in this test.)
            content: "Exit edit mode",
            trigger: ".o_we_website_top_actions button.btn-primary:contains('Save_Parseltongue')",
            run: "click",
        },
        {
            content: "Wait for editor to be closed",
            trigger: ":iframe body:not(.editor_enable)",
        },
        // verify configurator page templates exist in landing pages category.
        {
            content: "Open create content menu",
            trigger: ".o_new_content_container a",
            run: "click",
        },
        {
            content: "Create a new page",
            trigger: "a[title='New Page']",
            run: "click",
        },
        {
            content: "Wait for page load and then verify landing page templates",
            trigger: "body",
            async run() {
                try {
                    await waitFor("a[data-id='landing']", { timeout: 5000 });
                    const landingTabEl = document.querySelector("a[data-id='landing']");
                    if (landingTabEl) {
                        landingTabEl.click();
                    }
                    // Wait for the templates to load
                    setTimeout(() => {
                        const templateCount = document.querySelectorAll(
                            ".o_website_page_templates_pane.active .o_page_template"
                        ).length;
                        // 6 default templates in landing pages category
                        if (templateCount === 6) {
                            console.error(
                                "Landing Pages category does not include configurator page templates and should contain more than six templates."
                            );
                        }
                    }, 2000);
                } catch (error) {
                    console.error("Timeout waiting for page load: ", error);
                }
            },
        },
]});
