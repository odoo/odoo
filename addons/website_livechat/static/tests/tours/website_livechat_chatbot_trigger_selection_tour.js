import { waitForMessage } from "@im_livechat/../tests/tours/livechat_tour_utils";

import { registry } from "@web/core/registry";

// Soft restart accumulates messages in the DOM; target the occurrence from the current run.
const answerBothQuestions = (index) => [
    waitForMessage("Hello, here is a first question?", { index }),
    {
        trigger: ".o-livechat-root:shadow button:contains(Yes to first question)",
        run: "click",
    },
    waitForMessage("Hello, here is a second question?", { index }),
    {
        trigger: ".o-livechat-root:shadow button:contains(No to second question)",
        run: "click",
    },
];
registry.category("web_tour.tours").add("website_livechat.chatbot_trigger_selection", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        ...answerBothQuestions(0),
        {
            trigger: ".o-livechat-root:shadow button[title='Restart Conversation']",
            run: "click",
        },
        ...answerBothQuestions(1),
        {
            trigger: ".o-livechat-root:shadow button[title='Restart Conversation']",
        },
    ],
});
