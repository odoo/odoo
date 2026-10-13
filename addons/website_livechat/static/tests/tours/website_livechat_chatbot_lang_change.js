import { registry } from "@web/core/registry";

const messagesContain = (text) => `.o-livechat-root:shadow .o-mail-Message:contains("${text}")`;

registry.category("web_tour.tours").add("website_livechat_chatbot_lang_change", {
    steps: () => [
        {
            trigger: messagesContain("Hello! I'm a bot!"),
        },
        {
            content: "Switch the website to French",
            trigger: messagesContain("How can I help you?"),
            run: () => (location.href = "/fr"),
            expectUnloadPage: true,
        },
        {
            trigger: messagesContain("Bonjour ! Je suis un bot !"),
        },
        {
            trigger: messagesContain("Comment puis-je vous aider ?"),
        },
        {
            trigger: ".o-livechat-root:shadow li:contains(Question de prix)",
        },
    ],
});
