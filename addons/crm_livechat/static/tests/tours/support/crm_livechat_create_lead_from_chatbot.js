import { postMessage, waitForMessage } from "@im_livechat/../tests/tours/livechat_tour_utils";

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("crm_livechat.create_lead_from_chatbot", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        waitForMessage("Hello, how can I help you?"),
        ...postMessage("I'd like to know more about the CRM application."),
        waitForMessage("Would you mind leaving your email address so that we can reach you back?"),
        ...postMessage("visitor@example.com"),
        waitForMessage("Thank you, you should hear back from us very soon!"),
    ],
});
