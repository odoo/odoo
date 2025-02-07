import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { waitFor } from "@odoo/hoot-dom";

function waitForSelector(selector) {
    return [
        {
            content: `Wait for ${selector}`,
            trigger: "body",
            async run() {
                return waitFor(selector, {
                    timeout: 5000,
                });
            },
        },
    ];
}

registry.category("web_tour.tours").add("configurator_pages", {
    url: "/website/configurator",
    steps: () => [
    // Configurator first screen
    {
        content: "Click next",
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
        trigger: ".o_configurator_industry_wrapper ul li a:contains('abbey')",
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
        content: "Click on build my website",
        trigger: "button.btn-primary",
        run: "click",
    },
    {
        content: "Wait until the configurator is finished",
        trigger: ".o_website_preview[data-view-xmlid='website.homepage']",
        timeout: 30000,
    },
    stepUtils.waitIframeIsReady(),
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
    ...waitForSelector("a[data-id='landing']"),
    {
        content: "Click on the 'Landing Pages' tab",
        trigger: "a[data-id='landing']",
        run: "click",
    },
    {
        content: "Check if Landing Pages category contains configurator page templates",
        trigger: ".o_website_page_templates_pane.active",
        run: function () {
            let templateCount = document.querySelectorAll(".o_website_page_templates_pane.active .o_page_template").length;
            // 6 default templates in landing pages category
            if (templateCount === 6) {
                console.error("Landing Pages category does not have configurator page templates");
            }
        },
    },
]});
