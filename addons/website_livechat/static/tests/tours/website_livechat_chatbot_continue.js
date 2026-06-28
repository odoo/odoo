import { waitForMessage } from "@im_livechat/../tests/tours/livechat_tour_utils";

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat.chatbot_continue_tour", {
    steps: () => [
        waitForMessage("Hello, what can I do for you?"),
        {
            trigger: ".o-livechat-root:shadow button:contains(No, thank you for your time.)",
            run: "click",
        },
        {
            trigger:
                ".o-livechat-root:shadow span:contains(This live chat conversation has ended.)",
        },
        {
            trigger: ".o-livechat-root:shadow button[title='Give your feedback']",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow *:contains(Did we correctly answer your question?)",
        },
    ],
});
