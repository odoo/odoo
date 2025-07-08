import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("mail_message_edit_remove_preview_tour", {
    steps: () => [
        {
            trigger: ".o-mail-Message[data-persistent]",
            run: "hover",
        },
        {
            trigger: '.o-mail-Message [title="Expand"]',
            run: "click",
        },
        {
            trigger: '.o-mail-Message-moreMenu [title="Edit"]',
            run: "click",
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "edit Hi",
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger: ".o-mail-Message[data-persistent]:contains(Hi)",
        },
    ],
});
