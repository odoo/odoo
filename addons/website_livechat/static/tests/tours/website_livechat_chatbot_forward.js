import { postMessage, waitForMessage } from "@im_livechat/../tests/tours/livechat_tour_utils";

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat.chatbot_forward", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        waitForMessage("Hello, what can I do for you?"),
        {
            trigger: ".o-livechat-root:shadow button:contains(Forward to operator)",
            run: "click",
        },
        waitForMessage("I'll forward you to an operator."),
        ...postMessage("Hello, I need help!"),
        waitForMessage("Hello, I need help!"),
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-html:enabled",
            run: function () {
                window.location.reload();
            },
            expectUnloadPage: true,
        },
        ...postMessage("Hello, I accidentally refreshed!"),
        waitForMessage("Hello, I accidentally refreshed!"),
    ],
});
