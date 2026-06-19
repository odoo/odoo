import { postMessage, waitForMessage } from "@im_livechat/../tests/tours/livechat_tour_utils";

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat_user_known_after_reload", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        ...postMessage("Hello, I need help!"),
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-Thread:not([data-transient]) .o-mail-Message:contains('Hello, I need help!').o-selfAuthored ",
            run() {
                window.location.reload();
            },
            expectUnloadPage: true,
        },
        waitForMessage("Hello, I need help!", { selfAuthored: true }),
    ],
});
