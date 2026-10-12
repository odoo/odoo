import { postMessage, waitForMessage } from "@im_livechat/../tests/tours/livechat_tour_utils";

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat.chatbot_stop_when_agent_joins_tour", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        waitForMessage("Enter your phone number"),
        ...postMessage("+919876543210"),
        waitForMessage("Enter your email address"),
        ...postMessage("test@example.com"),
        {
            trigger: ".o-livechat-root:shadow button:contains(Try again)",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow span:contains(joined the conversation)",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-ChatWindow:not(:has(button:contains(retry)))",
        },
        ...postMessage("hello agent"),
        waitForMessage("hello agent"),
    ],
});
