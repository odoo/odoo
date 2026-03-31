import { expirableStorage } from "@im_livechat/core/common/expirable_storage";
import { browser } from "@web/core/browser/browser";
import { serializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export class HistoryService {
    static HISTORY_STORAGE_KEY = "im_livechat_history";
    static HISTORY_LIMIT = 15;
    static HISTORY_EXPIRY = 60 * 60 * 24; // 1 day

    constructor(env, services) {
        /** @type {ReturnType<typeof import("@bus/services/bus_service").busService.start>} */
        this.busService = services.bus_service;
        /** @type {import("models").Store} */
        this.store = services["mail.store"];
    }

    setup() {
        this.updateHistory();
        this.busService.subscribe("im_livechat.history_command", async (payload) => {
            const channel = await this.store["discuss.channel"].getOrFetch(payload.id);
            if (channel?.channel_type !== "livechat") {
                return;
            }
            rpc("/im_livechat/history", {
                pid: payload.partner_id,
                channel_id: channel.id,
                page_history: this.getHistory(),
            });
        });
    }

    getHistory() {
        const pageHistory = expirableStorage.getItem(HistoryService.HISTORY_STORAGE_KEY);
        if (!pageHistory) {
            return [];
        }
        const data = JSON.parse(pageHistory);
        return data.map((e) => {
            if (typeof e === "string") {
                return { url: e, title: e, visited_at: null };
            }
            return e;
        });
    }

    updateHistory() {
        const page = browser.location.href;
        const history = this.getHistory();
        history.push({
            title: document.title || page.replace(/^.*\/\/[^/]+/, ""),
            url: page,
            visited_at: serializeDateTime(luxon.DateTime.utc().startOf("second")),
        });
        expirableStorage.setItem(
            HistoryService.HISTORY_STORAGE_KEY,
            JSON.stringify(history.slice(-HistoryService.HISTORY_LIMIT)),
            HistoryService.HISTORY_EXPIRY
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
