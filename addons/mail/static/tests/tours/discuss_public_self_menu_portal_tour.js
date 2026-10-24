import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss_public_self_menu_portal_tour.js", {
    steps: () => [
        {
            trigger: ".o-mail-Thread",
        },
        {
            trigger:
                ".o-mail-PublicSelfMenu-toggler:has(.o-mail-PublicSelfMenu-name:text(Portal Bowser))",
            run: "click",
        },
        {
            content: "Only guests can change their name from the menu",
            trigger:
                ".o-mail-PublicSelfMenu:has(.o-mail-PublicSelfMenu-colorSchemeToggler):not(:has(.o-mail-PublicSelfMenu-guestName)):not(:has(.dropdown-divider))",
        },
    ],
});
