import { registry } from "@web/core/registry";
import { rpcBus } from "@web/core/network/rpc";

registry.category("web_tour.tours").add("website_livechat.chatbot_user_input_saved_on_last_step", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Message:contains(Enter your phone number)",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "edit +919876543210",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Message:contains(Enter your email address)",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "edit test@example.com",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            async run(helpers) {
                // We wait for the request to complete to ensure the final user input is persisted in the database before moving forward.
                let requestId;
                rpcBus.addEventListener("RPC:REQUEST", function onRequest({ detail }) {
                    if (detail.url === "/chatbot/step/trigger") {
                        requestId = detail.data.id;
                        rpcBus.removeEventListener("RPC:REQUEST", onRequest);
                    }
                });
                await helpers.press("ENTER");
                await new Promise((resolve) => {
                    rpcBus.addEventListener("RPC:RESPONSE", function onResponse({ detail }) {
                        if (detail.data.id === requestId) {
                            rpcBus.removeEventListener("RPC:RESPONSE", onResponse);
                            resolve();
                        }
                    });
                });
            },
        },
        {
            trigger: ".o-livechat-root:shadow span:contains(This livechat conversation has ended)",
        },
    ],
});
