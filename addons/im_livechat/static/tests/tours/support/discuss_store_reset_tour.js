import {
    getAfterResetSteps,
    getSendFirstMessageAndResetSteps,
} from "@mail/../tests/tours/discuss_store_reset_tour";

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("im_livechat.store_reset_in_embed_livechat", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        ...getSendFirstMessageAndResetSteps(".o-livechat-root:shadow"),
        ...getAfterResetSteps(".o-livechat-root:shadow"),
    ],
});
