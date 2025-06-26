import { registry } from "@web/core/registry";
import { closeChat } from "./website_livechat_common";

const messagesContain = (text) => `.o-livechat-root:shadow .o-mail-Message:contains("${text}")`;

registry.category("web_tour.tours").add("website_livechat_chatbot_after_reload_tour", {
    steps: () => [
        {
            trigger: messagesContain("Hello! I'm a bot!"),
            run: "click",
        },
        {
            content: "Reload the page",
            trigger: messagesContain("How can I help you?"),
            run: () => location.reload(),
        },
        ...closeChat,
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        {
            trigger: messagesContain("Hello! I'm a bot!"),
        },
    ],
});
