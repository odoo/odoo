import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_event_pages_seo", {
    // The tour must start on an event's custom page (not register page)
    // url: `/event/openwood-collection-online-reveal-8/page/home-openwood-collection-online-reveal`,
    steps: () => [
        {
            trigger: ":iframe #o_wevent_event_submenu", // Ensure we landed on the event page
        },
        {
            content: "Open the site menu",
            trigger: '[data-menu-xmlid="website.menu_site"]',
            run: "click",
        },
        {
            content: "Open the optimize SEO dialog",
            trigger: '[data-menu-xmlid="website.menu_optimize_seo"]',
            run: "click",
        },
        {
            content: "Fill in the title input",
            trigger: '.modal [for="website_meta_title"] + input',
            run: "edit Hello, world!",
        },
        {
            content: "Save the dialog",
            trigger: ".modal .modal-footer .btn-primary",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
        {
            trigger: ":iframe head:has(title:text(Hello, world!)):not(:visible)",
        },
        {
            content: "Check that the page title is adapted, inside and outside the iframe",
            trigger: "head:has(title:text(Hello, world!)):not(:visible)",
        },
    ],
});
