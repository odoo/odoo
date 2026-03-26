import { reactive } from "@web/owl2/utils";
import { markRaw, onWillDestroy } from "@odoo/owl";
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
    // Main emoji data
    /** @type {EmojiCategory[]} */
    categories = [];
    /** @type {Emoji[]} */
    emojis = [];

    // Derived emoji data
    get loaded() {
        return this.emojis.length > 0;
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
            this._map = markRaw(new Map());
            for (const emoji of this.emojis) {
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

    // Loader metadata
    /**
     * @private
     * @type {Promise<EmojiLoader> & { abort: () => void } | null}
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
     */
    load() {
        if (!this._loadingPromise) {
            let aborted = false;
            this._loadingPromise = this.loadEmojiBundle()
                .then(() => {
                    if (aborted) {
                        return Promise.reject("loading aborted");
                    }
                    const { categories, emojis } = processEmojiData();
                    this.categories = markRaw(categories);
                    this.emojis = markRaw(emojis);
                    return this;
                })
                .catch(() => {
                    // Failure: could be intentional (tour ended successfully while emoji still loading)
                    // -> returns forever promise
                    this._loadingPromise = null;
                    return new Promise(() => {});
                });
            this._loadingPromise.abort = function abort() {
                aborted = true;
            };
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

/** @type {Map<string, Emoji> | null} */
const DEFAULT_EMOJI_MAP = markRaw(new Map());

export function useLoadEmoji() {
    let abort = null;
    onWillDestroy(() => abort?.());
    return function loadEmoji() {
        const promise = emojiLoader.load();
        abort = promise.abort;
        return promise;
    };
}

export const emojiLoader = reactive(new EmojiLoader());
