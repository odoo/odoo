import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";

export const livechatInitializedService = {
    start() {
        return {
            ready: new Deferred(),
        };
    },
};
registry.category("services").add("im_livechat.initialized", livechatInitializedService);
