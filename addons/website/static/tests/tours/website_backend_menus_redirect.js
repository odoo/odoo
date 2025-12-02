import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_backend_menus_redirect", {
    url: "/",
    steps: () => [
        {
            isActive: ["enterprise"],
            content: "Need at least a step so the tour is not failing in enterprise",
            trigger: "body",
        },
        {
            isActive: ["community"],
            content: "Make frontend to backend menus appears",
            trigger: "body:has(#wrap)",
            run: function () {
                // The dropdown is hidden behind an SVG on hover animation.
                this.anchor.querySelector(".o_frontend_to_backend_apps_menu").classList.add("show");
            },
        },
        {
            isActive: ["community"],
            content: "Click on Test Root backend menu",
            trigger: '.o_frontend_to_backend_apps_menu a:contains("Test Root")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            isActive: ["community"],
            content:
                "Check that we landed on the apps page (Apps), and not the Home Action page (Settings)",
            // It cannot be the name of the menu here, as that would still be
            // displayed even when the default home action would be loaded. So
            // instead, use a class used by the Apps Kanban.
            trigger: ".oe_module_flag:not(:visible)",
        },
    ],
});
