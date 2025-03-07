import { registry } from "@web/core/registry";
import { delay } from "@odoo/hoot-dom";

registry.category("web_tour.tours").add("website_livechat.chatbot_redirect", {
    url: "/contactus",
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-Message:contains(Hello, were do you want to go?)",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow button:contains(Go to the #chatbot-redirect anchor)",
            run: "click",
        },
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-Message:contains(Tadam, we are on the page you asked for!)",
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
            trigger: ".o-livechat-root:shadow button[title='Restart Conversation']",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow button:contains(Go to the /chatbot-redirect page)",
            run: "click",
            expectUnloadPage: true,
        },
        {
            isActive: ["desktop"],
            trigger:
                ".o-livechat-root:shadow .o-mail-Message:contains('Go to the /chatbot-redirect page')",
        },
        {
            isActive: ["mobile"], //chatwindow is folded on mobile
            trigger: ".o-livechat-root:shadow .o-mail-ChatBubble[name='Redirection Bot']",
            async run(helpers) {
                await delay(500);
                await helpers.click();
            },
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Message:last:contains('Tadam')",
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
