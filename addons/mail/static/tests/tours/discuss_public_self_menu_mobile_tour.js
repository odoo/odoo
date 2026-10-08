import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss_public_self_menu_mobile_tour.js", {
    steps: () => [
        {
            trigger: ".o-mail-ChatWindow .o-mail-Thread",
        },
        {
            content: "Only the avatar is shown in the chat window header, the name is its title",
            trigger:
                ".o-mail-ChatWindow-header .o-mail-PublicSelfMenu-toggler[title='Guest Mario']",
            run: "click",
        },
        {
            trigger: ".o-mail-PublicSelfMenu-guestName",
            run: "edit Guest Luigi && press Enter",
        },
        {
            trigger:
                ".o-mail-ChatWindow-header .o-mail-PublicSelfMenu-toggler[title='Guest Luigi']",
        },
    ],
});
