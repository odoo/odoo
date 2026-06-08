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
    ],
});
