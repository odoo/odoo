import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat_as_portal_tour", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "edit Hello, I need help!",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Message:contains('Hello, I need help!')",
        },
    ],
});
