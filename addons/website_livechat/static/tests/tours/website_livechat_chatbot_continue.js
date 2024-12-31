import { registry } from "@web/core/registry";

const messagesContain = (text) => `.o-livechat-root:shadow .o-mail-Message:contains("${text}")`;

registry.category("web_tour.tours").add("website_livechat.chatbot_continue_tour", {
    steps: () => [
        {
            trigger: messagesContain("Hello, what can I do for you?"),
        },
        {
            trigger: ".o-livechat-root:shadow li:contains(No, thank you for your time.)",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow span:contains(Conversation ended...)",
        },
        {
            trigger: ".o-livechat-root:shadow button:contains(Continue)",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow *:contains(Did we correctly answer your question?)",
        },
    ],
});
