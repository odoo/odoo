import { waitForMessage } from "@im_livechat/../tests/tours/livechat_tour_utils";

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat_chatbot_after_reload_tour", {
    steps: () => [
        waitForMessage("Hello! I'm a bot!"),
        {
            content: "Reload the page",
            ...waitForMessage("How can I help you?"),
            run: () => location.reload(),
            expectUnloadPage: true,
        },
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        waitForMessage("Hello! I'm a bot!"),
        // Welcome steps are replayed from the ones the client already knows.
        waitForMessage("How can I help you?"),
        {
            trigger: '.o-livechat-root:shadow button:text("I\'d like to buy the software")',
            run: "click",
        },
        waitForMessage("Can you give us your email please?"),
        {
            trigger: ".o-livechat-root:shadow [title='Close Chat Window (ESC)']",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow button:contains('Yes, leave conversation')",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow button:contains('New Session')",
            run: "click",
        },
        waitForMessage("How can I help you?"),
        {
            content: "Answers of the replayed question are selectable again",
            trigger: '.o-livechat-root:shadow button:enabled:text("Pricing Question")',
        },
    ],
});
