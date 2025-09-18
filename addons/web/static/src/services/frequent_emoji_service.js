// @ts-check

/** @module @web/services/frequent_emoji_service - Tracks and retrieves frequently used emojis from localStorage */

import { reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
/**
 * @typedef {Object} FrequentEmojiState
 * @property {Record<string, number>} all - map of codepoints to usage counts
 * @property {(codepoints: string) => void} incrementEmojiUsage
 * @property {(limit?: number) => string[]} getMostFrequent
 */

/** Service that tracks frequently used emojis in localStorage. */
export const frequentEmojiService = {
    /** @returns {FrequentEmojiState} */
    start() {
        const state = reactive({
            /** @type {Record<string, number>} */
            all: JSON.parse(browser.localStorage.getItem("web.emoji.frequent") || "{}"),
            /**
             * Increment usage count for the given emoji codepoints.
             * @param {string} codepoints - the emoji codepoints identifier
             */
            incrementEmojiUsage(codepoints) {
                state.all[codepoints] ??= 0;
                state.all[codepoints]++;
                browser.localStorage.setItem(
                    "web.emoji.frequent",
                    JSON.stringify(state.all),
                );
            },
            /**
             * Return the most frequently used emoji codepoints, sorted by usage.
             * @param {number} [limit] - max number of results (defaults to all)
             * @returns {string[]} codepoints sorted by descending usage
             */
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
