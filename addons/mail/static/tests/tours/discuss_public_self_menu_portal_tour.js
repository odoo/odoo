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
                ".o-mail-PublicSelfMenu:has(.o-mail-PublicSelfMenu-colorScheme):not(:has(.o-mail-PublicSelfMenu-guestName)):not(:has(.dropdown-divider))",
        },
    ],
});

registry.category("web_tour.tours").add("discuss_public_self_menu_portal_without_menu_tour", {
    steps: () => [
        {
            trigger: ".o-mail-Thread",
        },
        {
            content: "Without a color scheme to pick, portal users have nothing to open",
            trigger:
                ".o-mail-MessagingMenu-self:has(.o-mail-PublicSelfMenu-name:text(Portal Bowser)):not(:has(.o-mail-PublicSelfMenu-toggler))",
        },
    ],
});
