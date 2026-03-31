import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat.chatbot_stop_when_agent_joins_tour", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Message:contains(Enter your phone number)",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "edit +919876543210",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Message:contains(Enter your email address)",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "edit test@example.com",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger: ".o-livechat-root:shadow button:contains(Try again)",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow span:contains(joined the conversation)",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-ChatWindow:not(:has(button:contains(retry)))",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input:enabled",
            run: "edit hello agent",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Message:contains(hello agent)",
        },
    ],
});
