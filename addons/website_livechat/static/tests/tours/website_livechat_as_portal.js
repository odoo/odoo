import { postMessage, waitForMessage } from "@im_livechat/../tests/tours/livechat_tour_utils";

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat_as_portal_tour", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        ...postMessage("Hello, I need help!"),
        waitForMessage("Hello, I need help!"),
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-ChatWindow .o-mail-Thread:not([data-transient])",
        },
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-ChatWindow-header [title='Open Actions Menu']",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow .o-dropdown-item:contains('Open in Discuss')",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: ".o-mail-DiscussContent .o-mail-Message-body:text('Hello, I need help!')",
            run() {
                if (!/^\/discuss\/channel\/\d+$/.test(window.location.pathname)) {
                    throw new Error(
                        `Expected public Discuss channel, got ${window.location.pathname}`
                    );
                }
            },
        },
    ],
});
