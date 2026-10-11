import { Thread } from "@mail/core/common/thread_model";
import { patchModel } from "@mail/model/export";

export const threadPatch = patchModel(Thread, {
    /**
     * @param {string[]} requestList
     * @param {Object} [options]
     * @param {MessageRouteParams} [options.messageFetchRouteParams]
     */
    async fetchThreadData(requestList, { messageFetchRouteParams = {} } = {}) {
        if (requestList.includes("messages")) {
            this.fetchNewMessages({ routeParams: messageFetchRouteParams });
        }
        await this.store.fetchStoreData("mail.thread", {
            access_params: this.rpcParams,
            request_list: requestList.filter((r) => r !== "messages"),
            thread_id: this.id,
            thread_model: this.model,
        });
    },

    /** @returns {string[]} */
    get fullComposerCloseRequestList() {
        return ["messages"];
    },
});
