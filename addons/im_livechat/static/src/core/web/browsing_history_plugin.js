import { BusPlugin } from "@bus/services/bus_plugin";

import { onWillDestroy, Plugin, usePlugin } from "@odoo/owl";

import { ORM } from "@web/core/orm_plugin";
import { services } from "@web/core/services";
import { uuid } from "@web/core/utils/strings";

export class BrowsingHistoryPlugin extends Plugin {
    static HISTORY_REQUEST_TIMEOUT = 10_000;
    bus = usePlugin(BusPlugin);
    orm = usePlugin(ORM);
    /** @type {Map<number, { channel: import("models").DiscussChannel; requestId: string; timeoutId: number }>} */
    pendingRequests = new Map();

    setup() {
        const unsubscribe = this.bus.subscribe("im_livechat.history/response", (payload) => {
            const { channel_id, request_id, page_history } = payload;
            const pendingRequest = this.pendingRequests.get(channel_id);
            if (pendingRequest?.requestId !== request_id) {
                return;
            }
            const channel = pendingRequest.channel;
            channel.browsingHistory = page_history;
            channel.browsingHistoryStatus = "ready";
            this.clearRequest(channel.id);
        });
        onWillDestroy(() => {
            unsubscribe();
            for (const channelId of this.pendingRequests.keys()) {
                this.clearRequest(channelId);
            }
        });
    }

    /** @param {number} channelId */
    clearRequest(channelId) {
        clearTimeout(this.pendingRequests.get(channelId)?.timeoutId);
        this.pendingRequests.delete(channelId);
    }

    /** @param {import("models").DiscussChannel} channel */
    async request(channel) {
        this.clearRequest(channel.id);
        if (channel.livechat_end_dt) {
            if (channel.browsingHistoryStatus !== "ready") {
                channel.browsingHistoryStatus = "unavailable";
            }
            return;
        }
        const requestId = uuid();
        channel.browsingHistoryStatus = "loading";
        const onError = () => {
            if (this.pendingRequests.get(channel.id)?.requestId !== requestId) {
                return;
            }
            this.clearRequest(channel.id);
            channel.browsingHistoryStatus = channel.livechat_end_dt ? "unavailable" : "error";
        };
        this.pendingRequests.set(channel.id, {
            channel,
            requestId,
            timeoutId: setTimeout(onError, BrowsingHistoryPlugin.HISTORY_REQUEST_TIMEOUT),
        });
        try {
            await this.orm.call("discuss.channel", "request_browsing_history", [
                [channel.id],
                requestId,
            ]);
        } catch (e) {
            onError();
            throw e;
        }
    }
}

services.add(BrowsingHistoryPlugin);
