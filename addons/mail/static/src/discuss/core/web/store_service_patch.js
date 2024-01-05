/* @odoo-module */

import { Store } from "@mail/core/common/store_service";

import { rpc } from "@web/core/network/rpc";
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
        rpc("/discuss/channels").then(
            (channelsData) => {
                this.Thread.insert(channelsData);
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
