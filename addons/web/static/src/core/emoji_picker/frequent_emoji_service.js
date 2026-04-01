import { reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export const frequentEmojiService = {
    start() {
        const state = reactive({
            all: JSON.parse(browser.localStorage.getItem("web.emoji.frequent") || "{}"),
            incrementEmojiUsage(codepoints) {
                state.all[codepoints] ??= 0;
                state.all[codepoints]++;
                browser.localStorage.setItem("web.emoji.frequent", JSON.stringify(state.all));
            },
            getMostFrequent(limit) {
                return Object.entries(state.all)
                    .sort(([, usage_1], [, usage_2]) => usage_2 - usage_1)
                    .slice(0, limit ?? Infinity)
                    .map(([codepoints]) => codepoints);
            },
        });
        browser.addEventListener("storage", (ev) => {
            if (ev.key === "web.emoji.frequent") {
                state.all = ev.newValue ? JSON.parse(ev.newValue) : {};
            } else if (ev.key === null) {
                state.all = {};
            }
        });
        return state;
    },
};

registry.category("services").add("web.frequent.emoji", frequentEmojiService);
