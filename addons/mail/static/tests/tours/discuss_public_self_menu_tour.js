import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss_public_self_menu_tour.js", {
    steps: () => [
        {
            trigger: ".o-mail-Thread",
        },
        {
            trigger:
                ".o-mail-PublicSelfMenu-toggler:has(.o-mail-PublicSelfMenu-name:text(Guest Mario))",
            run: "click",
        },
        {
            trigger: ".o-mail-PublicSelfMenu-guestName",
            run: "edit Guest Luigi && press Enter",
        },
        {
            trigger: ".o-mail-PublicSelfMenu-toggler .o-mail-PublicSelfMenu-name:text(Guest Luigi)",
        },
    ],
});
