import { postMessage } from "@im_livechat/../tests/tours/livechat_tour_utils";

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat_logout_after_chat_start", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        ...postMessage("Hello!"),
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-Thread:not([data-transient]) .o-mail-Message-content:contains('Hello!')",
            run: "click",
        },
        {
            trigger: "header#top a:contains(Mitchell Admin)",
            run: "click",
        },
        {
            trigger: "button:contains(Logout)",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content:
                "Livechat button is present since the old livechat session was linked to the logged user, not the public one.",
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
        },
    ],
});
