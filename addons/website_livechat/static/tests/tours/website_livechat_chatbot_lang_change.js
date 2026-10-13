/* @odoo-module */

import { registry } from "@web/core/registry";

const messagesContain = (text) => `.o-mail-Message:contains("${text}")`;

registry.category("web_tour.tours").add("website_livechat_chatbot_lang_change", {
    test: true,
    shadow_dom: ".o-livechat-root",
    steps: () => [
        {
            trigger: messagesContain("Hello! I'm a bot!"),
        },
        {
            content: "Switch the website to French",
            trigger: messagesContain("How can I help you?"),
            run: () => (location.href = "/fr"),
        },
        {
            trigger: messagesContain("Bonjour ! Je suis un bot !"),
        },
        {
            trigger: messagesContain("Comment puis-je vous aider ?"),
        },
        {
            trigger: "li:contains(Question de prix)",
            isCheck: true,
        },
    ],
});
