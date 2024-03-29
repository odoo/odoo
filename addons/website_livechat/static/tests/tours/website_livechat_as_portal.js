import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat_as_portal_tour", {
    test: true,
    shadow_dom: ".o-livechat-root",
    steps: () => [
        {
            trigger: ".o-livechat-LivechatButton",
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "edit Hello, I need help!",
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger: ".o-mail-Message:contains('Hello, I need help!')",
            isCheck: true,
        },
    ],
});
