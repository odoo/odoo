import {
    editComposer,
    LIVECHAT_COMPOSER,
    postMessage,
    waitForMessage,
} from "@im_livechat/../tests/tours/livechat_tour_utils";

import { rpcBus } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat.chatbot_user_input_saved_on_last_step", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        waitForMessage("Enter your phone number"),
        ...postMessage("+919876543210"),
        waitForMessage("Enter your email address"),
        editComposer("test@example.com"),
        {
            trigger: `${LIVECHAT_COMPOSER}:enabled`,
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
            trigger:
                ".o-livechat-root:shadow span:contains(This live chat conversation has ended.)",
        },
    ],
});
