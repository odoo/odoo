import { localization } from "@web/core/l10n/localization";
import { translatedTermsGlobal } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { clickOnEditAndWaitEditMode } from "@website/js/tours/tour_utils";

function runConfiguratorFlow(industrySearchText) {
    return [
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
            content: "Choose from the positioning list",
            trigger: "button.o_change_website_purpose",
            run: "click",
        },
        // Palette screen
        {
            content: "Choose a palette card",
            trigger: ".palette_card",
            run: "click",
        },
        {
            content: "Go to the next configurator step",
            trigger: "button.o_configurator_next:not(:disabled)",
            run: "click",
        },
        {
            id: "loader",
            content: "Loader should be shown",
            trigger: ".o_website_loader_container",
            expectUnloadPage: true,
        },
        {
            content: "Wait until the configurator is finished",
            trigger: ":iframe [data-view-xmlid='website.homepage']",
            timeout: 30000,
        },
        {
            content: "Check that the editor, not translation mode, is opened",
            trigger:
                ":iframe html[data-editable='1']:not([data-translatable='1'][data-edit_translations='1'])",
        },
    ];
}

registry.category("web_tour.tours").add("configurator_translation", {
    steps: () => [
        ...runConfiguratorFlow("in fr"),
        {
            content: "Check if the current interface language is active and monkey patch terms",
            trigger: "body",
            run() {
                if (localization.code !== "pa_GB") {
                    throw new Error("The user language is not the correct one");
                } else {
                    translatedTermsGlobal["Save"] = "Save_Parseltongue";
                }
            },
        },
        ...clickOnEditAndWaitEditMode(),
        {
            // Check the content of the save button to make sure the website is in
            // Parseltongue. (The editor should be in the website's default language,
            // which should be parseltongue in this test.)
            content: "exit edit mode",
            trigger: ".o-snippets-top-actions button.btn-success:contains('Save_Parseltongue')",
            run: "click",
        },
        {
            content: "wait for editor to be closed",
            trigger: ":iframe #wrapwrap:not(.odoo-editor-editable)",
        },
    ],
});

registry.category("web_tour.tours").add("configurator_page_creation", {
    steps: () => [
        ...runConfiguratorFlow("abbey"),
        // Verify configurator page templates exist in the About Us category.
        {
            content: "Open create content menu",
            trigger: ".o_new_content_container button",
            run: "click",
        },
        {
            content: "Create a new page",
            trigger: "button[aria-label='New Page']",
            run: "click",
        },
        {
            content: "Click on About Us pages category",
            trigger: ".o_website_page_templates_dialog aside [data-id='about_us']",
            run: "click",
        },
        {
            content: "Check if configurator pages exist",
            trigger: "#pane_about_us .o_page_template[data-configurator-page]",
        },
        {
            content: "Configurator pages should appear at the start of the About Us category",
            trigger:
                "#pane_about_us .row > :first-child .o_page_template:first-of-type[data-configurator-page]",
        },
        {
            content: "Exit dialog",
            trigger: ".modal-header .btn-close",
            run: "click",
        },
    ],
});
