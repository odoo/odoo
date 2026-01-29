/* @odoo-module */

import { registry } from "@web/core/registry";
import { endDiscussion } from "./website_livechat_common";

const messagesContain = (text) => `.o-mail-Message:contains("${text}")`;

registry.category("web_tour.tours").add("website_livechat_chatbot_after_reload_tour", {
    test: true,
    shadow_dom: ".o-livechat-root",
    steps: () => [
        {
            trigger: messagesContain("Hello! I'm a bot!"),
        },
        {
            content: "Reload the page",
            trigger: messagesContain("How can I help you?"),
            run: () => location.reload(),
        },
        ...endDiscussion,
        {
            trigger: ".o-livechat-LivechatButton",
            run: "click",
        },
        {
            trigger: messagesContain("Hello! I'm a bot!"),
            run: () => {},
        },
    ],
});
