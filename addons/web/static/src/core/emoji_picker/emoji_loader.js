import { markRaw, onWillDestroy, reactive } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { escapeRegExp } from "@web/core/utils/strings";

/**
 * @typedef {{
 *  codepoints: string;
 *  emoticons: string[];
 *  keywords: string[];
 *  name: string;
 *  shortcodes: string[];
 * }} BaseEmoji
 *
 * @typedef {BaseEmoji & {
 *  category: EmojiCategory;
 * }} Emoji
 *
 * @typedef {{
 *  displayName: string;
 *  name: string;
 *  sortId: number;
 *  title: string;
 * }} EmojiCategory
 *
 * @typedef {BaseEmoji & {
 *  category: string;
 * }} RawEmoji
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
    /** @type {RawEmoji[]} */
    const emojis = Object.freeze(getEmojis());

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

    get regex() {
        if (!this.loaded) {
            // Not loaded: do not compute yet
            return DEFAULT_EMOJI_REGEX;
        }
        if (!this._regex) {
            /** @type {string[]} */
            const emojiRegexKeys = [];
            for (const emoji of this.emojis) {
                emojiRegexKeys.push(escapeRegExp(emoji.codepoints));
            }
            // Sort to get composed emojis first
            emojiRegexKeys.sort((a, b) => b.length - a.length);
            this._regex = new RegExp(emojiRegexKeys.join("|"), "gu");
        }
        return this._regex;
    }

    // Loader metadata
    /**
     * @private
     * @type {Promise<EmojiLoader> & { abort: () => void } | null}
     */
    _loadingPromise = null;
    /** @type {Map<string, Emoji> | null} */
    _map = null;
    /** @type {RegExp | null} */
    _regex = null;

    /**
     * Returns the first short code associated to a given emoji value.
     *
     * @param {string} value
     */
    getShortCode(value) {
        return this.map.get(value)?.shortcodes?.[0] ?? "?";
    }

    /**
     * Entry point to load emoji data
     *
     * This function is memoized on the 'emojiLoade' singleton, so it will always
     * return the same promise.
     */
    load() {
        if (!this._loadingPromise) {
            let aborted = false;
            this._loadingPromise = this.loadEmojiBundle()
                .then(() => {
                    if (aborted) {
                        return Promise.reject("loading aborted");
                    }
                    // Success: assigns loaded data and returns the loader
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

const DEFAULT_EMOJI_REGEX = /(?!)/gu;
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
