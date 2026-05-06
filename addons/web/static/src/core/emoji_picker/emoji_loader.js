import { signal, useScope } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";

/**
 * @typedef {{
 *  category: EmojiCategory;
 *  codepoints: string;
 *  emoticons: string[];
 *  keywords: string[];
 *  name: string;
 *  shortcodes: string[];
 * }} Emoji
 *
 * @typedef {{
 *  displayName: string;
 *  name: string;
 *  sortId: number;
 *  title: string;
 * }} EmojiCategory
 */

/**
 * @returns {{ categories: EmojiCategory[], emojis: Emoji[] }}
 */
function processEmojiData() {
    const { getCategories, getEmojis } = odoo.loader.modules.get(
        "@web/core/emoji_picker/emoji_data"
    );

    // Get and freeze categories & emojis (only list objects are frozen at this
    // point: internal objects are still writable).
    /** @type {EmojiCategory[]} */
    const categories = Object.freeze(getCategories());
    /** @type {(Emoji & { category: string })[]} */
    const emojis = Object.freeze(getEmojis());
    /** @type {Record<string, EmojiCategory>} */
    const categoryMap = {};
    for (const category of categories) {
        categoryMap[category.name] = category;

        // Freeze category object
        Object.freeze(category);
    }

    for (const emoji of emojis) {
        emoji.category = categoryMap[emoji.category];

        // Deep freeze emoji data
        Object.freeze(emoji);
        Object.freeze(emoji.emoticons);
        Object.freeze(emoji.keywords);
        Object.freeze(emoji.shortcodes);
    }

    return { categories, emojis };
}

class EmojiLoader {
    get categories() {
        return this._categories();
    }
    get emojis() {
        return this._emojis();
    }
    get loaded() {
        return this._emojis().length > 0;
    }
    /**
     * Mapping to emojis from:
     * - codepoints
     * - emoticons
     * - shortcodes
     */
    get map() {
        if (!this.loaded) {
            // Not loaded: do not compute yet
            return DEFAULT_EMOJI_MAP;
        }
        if (!this._map) {
            this._map = new Map();
            for (const emoji of this._emojis()) {
                this._map.set(emoji.codepoints, emoji);
                for (const emoticon of emoji.emoticons) {
                    this._map.set(emoticon, emoji);
                }
                for (const shortcode of emoji.shortcodes) {
                    this._map.set(shortcode, emoji);
                }
            }
        }
        return this._map;
    }

    /**
     * @private
     * @type {import("@odoo/owl").Signal<EmojiCategory[]>}
     */
    _categories = signal.Array([]);
    /**
     * @private
     * @type {import("@odoo/owl").Signal<Emoji[]>}
     */
    _emojis = signal.Array([]);
    /**
     * @private
     * @type {Promise<EmojiLoader>}
     */
    _loadingPromise = null;
    /**
     * @private
     * @type {Map<string, Emoji> | null}
     */
    _map = null;

    /**
     * Returns the first short code associated to a given emoji value.
     *
     * @param {string} value
     */
    getShortCode(value) {
        return this.map.get(value)?.shortcodes?.[0] ?? "?";
    }

    /**
     * Entry point to load emoji data (stored in
     * **`@web/core/emoji_picker/emoji_data.js`**).
     *
     * This function is memoized on the 'emojiLoader' singleton, so it will always
     * return the same promise.
     *
     * If the promise fails (e.g. by being aborted, or because it was run in a tour
     * that has ended), it is left pending forever, and the promise kept by the
     * loader is reset to allow retrying to fetch emoji data.
     * @param {AbortSignal} [abortSignal]
     */
    load(abortSignal) {
        if (!this._loadingPromise) {
            this._loadingPromise = this.loadEmojiBundle()
                .then(() => {
                    if (abortSignal?.aborted) {
                        return Promise.reject("loading aborted");
                    }
                    const { categories, emojis } = processEmojiData();
                    this._categories.set(categories);
                    this._emojis.set(emojis);
                    return this;
                })
                .catch(() => {
                    // Failure: could be intentional (tour ended successfully while emoji still loading)
                    // -> returns forever promise
                    this._loadingPromise = null;
                    return new Promise(() => {});
                });
        }
        return this._loadingPromise;
    }

    /**
     * Can be overridden on the `emojiLoader` instance to load a different bundle.
     */
    loadEmojiBundle() {
        return loadBundle("web.assets_emoji");
    }
}

/** @type {Map<string, Emoji>} */
const DEFAULT_EMOJI_MAP = new Map();

export function useLoadEmoji() {
    const { abortSignal } = useScope();
    return function loadEmoji() {
        return emojiLoader.load(abortSignal);
    };
}

export const emojiLoader = new EmojiLoader();
