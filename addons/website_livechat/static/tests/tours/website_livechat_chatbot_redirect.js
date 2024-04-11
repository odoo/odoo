/* @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat.chatbot_redirect", {
    shadow_dom: ".o-livechat-root",
    test: true,
    url: "/contactus",
    steps: () => [
        {
            trigger: ".o-livechat-LivechatButton",
        },
        {
            trigger: ".o-mail-Message:contains(Hello, were do you want to go?)",
        },
        {
            trigger: "li:contains(Go to the #chatbot-redirect anchor)",
        },
        {
            trigger: ".o-mail-Message:contains(Tadam, we are on the page you asked for!)",
            run() {
                const url = new URL(location.href);
                if (url.pathname !== "/contactus" || url.hash !== "#chatbot-redirect") {
                    throw new Error(
                        "Chatbot should have redirected to the #chatbot-redirect anchor."
                    );
                }
            },
        },
        {
            trigger: "button[title='Restart Conversation']",
        },
        {
            trigger: "li:contains(Go to the /chatbot-redirect page)",
        },
        {
            trigger:
                ".o-mail-Message:contains('Go to the /chatbot-redirect page') + .o-mail-Message:contains('Tadam')",
            run() {
                const url = new URL(location.href);
                if (url.pathname !== "/chatbot-redirect") {
                    throw new Error(
                        "Chatbot should have redirected to the /chatbot-redirect page."
                    );
                }
            },
        },
    ],
});
