import { registry } from "@web/core/registry";
import { reactive } from "@web/owl2/utils";

const STORAGE_KEY = "web.emoji.frequent";

export const frequentEmojiService = {
    start() {
        const state = reactive({
            /** @type {Record<string, number>} */
            all: JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}"),
            /**
             * @param {string} codepoints
             */
            incrementEmojiUsage(codepoints) {
                state.all[codepoints] ||= 0;
                state.all[codepoints]++;

                localStorage.setItem(STORAGE_KEY, JSON.stringify(state.all));
            },
            /**
             * @param {number} [limit]
             */
            getMostFrequent(limit) {
                let entries = Object.entries(state.all).sort(
                    ([, usage_1], [, usage_2]) => usage_2 - usage_1
                );
                if (limit) {
                    entries = entries.slice(0, limit);
                }
                return entries.map(([codepoints]) => codepoints);
            },
        });

        window.addEventListener("storage", (ev) => {
            if (ev.key === STORAGE_KEY) {
                state.all = ev.newValue ? JSON.parse(ev.newValue) : {};
            } else if (ev.key === null) {
                state.all = {};
            }
        });
        return state;
    },
};

registry.category("services").add("frequent_emoji", frequentEmojiService);
