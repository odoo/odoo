import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
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
            request_list: requestList,
            thread_id: this.id,
            thread_model: this.model,
        });
    },
});
