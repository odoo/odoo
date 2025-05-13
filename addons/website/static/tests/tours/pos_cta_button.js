import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("pos_cta_button", {
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
            trigger: ".o_configurator_industry_wrapper ul li a:contains('abbey')",
            run: "click",
        },
        {
            content: "Choose an objective from the list",
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
            content: "Wait until the configurator is finishes",
            trigger: ":iframe [data-view-xmlid='website.homepage']",
            timeout: 30000,
        },
        // Website Preview Screen
        {
            content: "Check the appointment menu is removed",
            trigger:
                ":iframe .top_menu:not(:has(.nav-item a[href='/appointment']:contains('Appointment')))",
        },
        {
            content: "Check the CTA button",
            trigger: ":iframe a[href='/appointment'].btn_cta:contains('Book a Table')",
        },
    ],
});
