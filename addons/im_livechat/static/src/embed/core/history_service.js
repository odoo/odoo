/* @odoo-module */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { expirableStorage } from "@im_livechat/embed/core/misc";

export class HistoryService {
    static HISTORY_KEY = "im_livechat_history";
    static HISTORY_LIMIT = 15;

    constructor(env, services) {
        /** @type {ReturnType<typeof import("@web/core/network/rpc_service").rpcService.start>} */
        this.rpc = services.rpc;
        /** @type {ReturnType<typeof import("@bus/services/bus_service").busService.start>} */
        this.busService = services.bus_service;
        /** @type {import("@im_livechat/embed/core/livechat_service").LivechatService} */
        this.livechatService = services["im_livechat.livechat"];
    }

    setup() {
        this.updateHistory();
        this.busService.subscribe("im_livechat.history_command", (payload) => {
            if (payload.id !== this.livechatService.thread?.id) {
                return;
            }
            const data = expirableStorage.getItem(HistoryService.HISTORY_KEY);
            const history = data ? JSON.parse(data) : [];
            this.rpc("/im_livechat/history", {
                pid: this.livechatService.thread.operator.id,
                channel_uuid: this.livechatService.thread.uuid,
                page_history: history,
            });
        });
    }

    updateHistory() {
        const page = browser.location.href.replace(/^.*\/\/[^/]+/, "");
        const pageHistory = expirableStorage.getItem(HistoryService.HISTORY_KEY);
        const urlHistory = pageHistory ? JSON.parse(pageHistory) : [];
        if (!urlHistory.includes(page)) {
            urlHistory.push(page);
            if (urlHistory.length > HistoryService.HISTORY_LIMIT) {
                urlHistory.shift();
            }
            expirableStorage.setItem(
                HistoryService.HISTORY_KEY,
                JSON.stringify(urlHistory),
                60 * 60 * 24 // kept for 1 day
            );
        }
    }
}

export const historyService = {
    dependencies: ["im_livechat.livechat", "bus_service", "rpc"],
    start(env, services) {
        const history = new HistoryService(env, services);
        history.setup();
    },
};

registry.category("services").add("im_livechat.history_service", historyService);
