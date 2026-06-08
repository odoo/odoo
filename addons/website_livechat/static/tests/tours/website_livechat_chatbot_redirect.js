import { waitForMessage } from "@im_livechat/../tests/tours/livechat_tour_utils";
import { Chatbot } from "@im_livechat/core/common/chatbot_model";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

registry.category("web_tour.tours").add("website_livechat.chatbot_redirect", {
    steps: () => {
        patch(Chatbot.prototype, {
            redirect: (url) => browser.open(url, "_self"),
        });
        return [
            {
                trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
                run: "click",
            },
            waitForMessage("Hello, were do you want to go?"),
            {
                trigger:
                    ".o-livechat-root:shadow button:contains(Go to the #chatbot-redirect anchor)",
                run: "click",
            },
            {
                ...waitForMessage("Tadam, we are on the page you asked for!"),
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
                trigger:
                    ".o-livechat-root:shadow button:contains(Go to the /chatbot-redirect page)",
                run: "click",
                expectUnloadPage: true,
            },
            {
                isActive: ["mobile"], //chatwindow is folded on mobile
                trigger: ".o-livechat-root:shadow .o-mail-ChatBubble[name='Redirection Bot']",
                run: "click",
            },
            waitForMessage("Go to the /chatbot-redirect page"),
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
        ];
    },
});
