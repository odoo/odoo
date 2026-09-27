import { postMessage, waitForMessage } from "@im_livechat/../tests/tours/livechat_tour_utils";

import { registry } from "@web/core/registry";

// The chatbot restart is a soft restart (no page reload), so messages accumulate in the
// DOM; pass the occurrence index to target the message posted by the current run.
const stepsUntilLastMessage = (index) => [
    waitForMessage("Enter your email address", { index }),
    ...postMessage("test@example.com"),
    waitForMessage("Do you want to restart the conversation?", { index }),
];

registry.category("web_tour.tours").add("website_livechat.chatbot_restart_on_feedback_tour", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        ...stepsUntilLastMessage(0),
        // restart in chat window
        {
            trigger: ".o-livechat-root:shadow button:contains(Yes, restart please.)",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow button[title='Restart Conversation']",
            run: "click",
        },
        ...stepsUntilLastMessage(1),
        // restart in feedback
        {
            trigger: ".o-livechat-root:shadow button:contains(Yes, restart please.)",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow button:contains(Continue)",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow div:contains(Did we correctly answer your question?)",
        },
        {
            trigger: ".o-livechat-root:shadow button[title='Restart Conversation']",
            run: "click",
        },
        ...stepsUntilLastMessage(2),
        // restart not displayed as chatbot did not finish
        {
            trigger: ".o-livechat-root:shadow button[title='Close Chat Window (ESC)']",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow button:contains(Yes, leave conversation)",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow div:contains(Did we correctly answer your question?)",
        },
        {
            trigger:
                '.o-livechat-root:shadow .o-mail-ChatWindow-header:not(:has(button[title="Restart Conversation"]))',
        },
    ],
});
