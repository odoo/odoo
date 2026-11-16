import { postMessage } from "@im_livechat/../tests/tours/livechat_tour_utils";

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("portal_chatter_reaction_with_livechat", {
    steps: () => [
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message:has(.o-mail-Message-body:text(Message on the task))",
            run: "hover",
        },
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message:has(.o-mail-Message-body:text(Message on the task)) button[title='Add a Reaction']",
        },
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        ...postMessage("Hello from the task"),
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-Thread:not([data-transient]) .o-mail-Message-body:text(Hello from the task)",
            run() {
                if (!localStorage.getItem("EXPIRABLE_STORAGE_im_livechat_guest_token")) {
                    throw new Error("The guest token of the visitor is not stored.");
                }
            },
        },
    ],
});
