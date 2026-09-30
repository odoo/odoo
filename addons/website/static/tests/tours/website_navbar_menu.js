import { registry } from "@web/core/registry";
import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registry.category("web_tour.tours").add("website_navbar_menu", {
    url: "/",
    steps: () => [
        {
            content: "Ensure menus are in DOM",
            trigger: ".top_menu .nav-item a:contains(Test Tour Menu)",
        },
        {
            content: "Ensure menus loading is done (so they are actually visible)",
            trigger: "body:not(:has(.o_menu_loading))",
        },
        {
            trigger: `.o_main_nav a[role="menuitem"]:contains(test tour menu)`,
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: `main:contains(We couldn't find the page you're looking for!)`,
        },
    ],
});

registerWebsitePreviewTour("website_systray_items_disappear", { url: "/" }, () => [
    {
        content: "Ensure frontend systray items have been added to the navbar",
        trigger: ".o_main_navbar .o_menu_systray:has(.o_edit_website_container)",
    },
    {
        content: "Open configuration dropdown",
        trigger: ".o_main_navbar button:contains(Configuration)",
        run: "click",
    },
    {
        content: "Go to settings",
        trigger: `.o_popover .o-dropdown-item:contains(Settings)`,
        run: "click",
    },
    {
        content: "Ensure frontend systray items have disappeared",
        trigger: `.o_main_navbar .o_menu_systray:not(:has(.o_edit_website_container, .o_new_content_container))`,
    },
]);
