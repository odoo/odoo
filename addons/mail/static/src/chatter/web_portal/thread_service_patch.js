import { ThreadService } from "@mail/core/common/thread_service";
import { rpcWithEnv } from "@mail/utils/common/misc";
/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;
import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, {
    setup(env, services) {
        rpc = rpcWithEnv(env);
        super.setup(env, services);
    },
    /**
     * @param {import("models").Thread} thread
     * @param {string[]} requestList
     */
    async fetchData(thread, requestList) {
        if (requestList.includes("messages")) {
            this.fetchNewMessages(thread);
        }
        const result = await rpc("/mail/thread/data", {
            request_list: requestList,
            thread_id: thread.id,
            thread_model: thread.model,
        });
        this.store.Thread.insert(result, { html: true });
        return result;
    },
});
