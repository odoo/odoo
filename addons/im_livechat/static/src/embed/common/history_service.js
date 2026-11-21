import { expirableStorage } from "@im_livechat/core/common/expirable_storage";
import { location } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export class HistoryService {
    static HISTORY_STORAGE_KEY = "im_livechat_history_20_1";
    static HISTORY_LIMIT = 3;

    constructor(env, services) {
        /** @type {ReturnType<typeof import("@bus/services/bus_plugin").busService.start>} */
        this.busService = services.bus_service;
        /** @type {import("models").Store} */
        this.store = services["mail.store"];
    }

    setup() {
        this.updateHistory();
        this.busService.subscribe("im_livechat.history/request", async (payload) => {
            const channel = await this.store["discuss.channel"].getOrFetch(payload.id);
            if (channel?.channel_type !== "livechat") {
                return;
            }
            rpc("/im_livechat/history", {
                pid: payload.partner_id,
                channel_id: channel.id,
                request_id: payload.request_id,
                page_history: this.getHistory().slice(0, HistoryService.HISTORY_LIMIT),
            });
        });
    }

    getHistory() {
        const data = expirableStorage.getItem(HistoryService.HISTORY_STORAGE_KEY);
        try {
            const history = JSON.parse(data);
            if (!Array.isArray(history)) {
                return [];
            }
            return history;
        } catch {
            return [];
        }
    }

    updateHistory() {
        const page = {
            title: document.title,
            url: location.href,
            visit_datetime: new Date().toISOString(),
        };
        const history = this.getHistory().filter((visit) => visit?.url !== page.url);
        history.unshift(page);
        expirableStorage.setItem(
            HistoryService.HISTORY_STORAGE_KEY,
            JSON.stringify(history.slice(0, HistoryService.HISTORY_LIMIT)),
            60 * 60 * 24 // kept for 1 day
        );
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
