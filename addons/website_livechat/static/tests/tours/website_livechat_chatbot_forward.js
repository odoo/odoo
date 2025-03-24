import { registry } from "@web/core/registry";

const messagesContain = (text) => `.o-livechat-root:shadow .o-mail-Message:contains("${text}")`;

registry.category("web_tour.tours").add("website_livechat.chatbot_forward", {
    url: "/",
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        {
            trigger: messagesContain("Hello, what can I do for you?"),
        },
        {
            trigger: ".o-livechat-root:shadow button:contains(Forward to operator)",
            run: "click",
        },
        {
            trigger: messagesContain("I'll forward you to an operator."),
        },
        {
            // Wait for the operator to be added: composer is only enabled at that point.
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input:enabled",
            run: "edit Hello, I need help!",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger: messagesContain("Hello, I need help!"),
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input:enabled",
        },
    ],
});
