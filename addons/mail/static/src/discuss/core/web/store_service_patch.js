/* @odoo-module */

import { Store } from "@mail/core/common/store_service";

import { Deferred } from "@web/core/utils/concurrency";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        this.fetchChannelsState = "not_fetched";
        this.fetchChannelsDeferred = undefined;
        this.initChannelsUnreadCounter = 0;
    },
    async fetchChannels() {
        if (["fetching", "fetched"].includes(this.fetchChannelsState)) {
            return this.fetchChannelsDeferred;
        }
        this.fetchChannelsState = "fetching";
        this.fetchChannelsDeferred = new Deferred();
        this.fetchData({ channels_as_member: true }).then(
            /**
             * @param {{ Message: import("models").Message[] }} recordsByModel
             */
            ({ Message: messages }) => {
                for (const message of messages) {
                    if (message.isNeedaction) {
                        message.originThread.needactionMessages.add(message);
                    }
                }
                this.fetchChannelsState = "fetched";
                this.fetchChannelsDeferred.resolve();
            },
            (error) => {
                this.fetchChannelsState = "not_fetched";
                this.fetchChannelsDeferred.reject(error);
            }
        );
        return this.fetchChannelsDeferred;
    },
};
patch(Store.prototype, StorePatch);
