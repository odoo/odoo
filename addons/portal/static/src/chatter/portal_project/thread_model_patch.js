import { Thread } from "@mail/core/common/thread_model";
import { patchModel } from "@mail/model/export";

export const threadPatch = patchModel(Thread, {
    get fetchRouteChatter() {
        return "/mail/chatter_fetch";
    },
});
