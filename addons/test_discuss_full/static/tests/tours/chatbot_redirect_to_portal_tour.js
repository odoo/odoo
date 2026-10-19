import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { browser } from "@web/core/browser/browser";
import { Chatbot } from "@im_livechat/core/common/chatbot_model";

registry.category("web_tour.tours").add("chatbot_redirect_to_portal", {
    steps: () => {
        patch(Chatbot.prototype, {
            redirect: (url) => browser.open(url, "_self"),
        });
        return [
            {
                trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
                run: "click",
            },
            {
                trigger:
                    ".o-livechat-root:shadow .o-mail-ChatWindow-header:contains(Redirection Bot)",
            },
            {
                trigger:
                    ".o-livechat-root:shadow .o-mail-Message:contains(Hello, were do you want to go?)",
                run: "click",
            },
            {
                trigger: ".o-livechat-root:shadow li button:contains(Go to the portal page)",
                run: "click",
                expectUnloadPage: true,
            },
            {
                trigger:
                    ".o-livechat-root:shadow .o-mail-Message:contains('Go to the portal page')",
            },
            { trigger: "#chatterRoot:shadow .o-mail-Chatter" },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Message:last:contains('Tadam')",
            },
        ];
    },
});
