import { expirableStorage } from "@im_livechat/core/common/expirable_storage";
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export class HistoryService {
    static HISTORY_STORAGE_KEY = "im_livechat_history";
    static HISTORY_LIMIT = 15;

    constructor(env, services) {
        /** @type {ReturnType<typeof import("@bus/services/bus_service").busService.start>} */
        this.busService = services.bus_service;
        /** @type {import("models").Store} */
        this.storeService = services["mail.store"];
    }

    setup() {
        this.updateHistory();
        this.busService.subscribe("im_livechat.history_command", async (payload) => {
            const thread = await this.storeService.Thread.getOrFetch({
                id: payload.id,
                model: "discuss.channel",
            });
            if (thread?.channel_type !== "livechat") {
                return;
            }
            const data = expirableStorage.getItem(HistoryService.HISTORY_STORAGE_KEY);
            const history = data ? JSON.parse(data) : [];
            rpc("/im_livechat/history", {
                pid: payload.partner_id,
                channel_id: thread.id,
                page_history: history,
            });
        });
    }

    updateHistory() {
        const page = browser.location.href.replace(/^.*\/\/[^/]+/, "");
        const pageHistory = expirableStorage.getItem(HistoryService.HISTORY_STORAGE_KEY);
        const urlHistory = pageHistory ? JSON.parse(pageHistory) : [];
        if (!urlHistory.includes(page)) {
            urlHistory.push(page);
            if (urlHistory.length > HistoryService.HISTORY_LIMIT) {
                urlHistory.shift();
            }
            expirableStorage.setItem(
                HistoryService.HISTORY_STORAGE_KEY,
                JSON.stringify(urlHistory),
                60 * 60 * 24 // kept for 1 day
            );
        }
    }
}

export const historyService = {
    dependencies: ["bus_service", "mail.store"],
    start(env, services) {
        const history = new HistoryService(env, services);
        history.setup();
    },
};

registry.category("services").add("im_livechat.history_service", historyService);
