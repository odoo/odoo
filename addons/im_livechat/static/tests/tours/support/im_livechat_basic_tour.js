import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("im_livechat.basic_tour", {
    steps: () => [
        {
            trigger: ".channel_name:contains(Support Channel)",
        },
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-ChatWindow",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Message",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-ChatWindow [title*='Close Chat Window']",
            run: "click",
        },
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-ChatHub:not(:visible):not(:has(.o-mail-ChatWindow))",
        },
    ],
});
