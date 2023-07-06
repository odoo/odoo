/* @odoo-module */

import { useStore } from "@mail/core/common/messaging_hook";
import { removeFromArrayWithPredicate } from "@mail/utils/common/arrays";
import { useOnBottomScrolled } from "@mail/utils/common/hooks";
import { markEventHandled } from "@web/core/utils/misc";;

import { Component, onWillStart, useRef, useState } from "@odoo/owl";

import { usePopover } from "@web/core/popover/popover_hook";
import { useService, useAutofocus } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

/**
 * @typedef {Object} TenorCategory
 * @property {string} searchterm
 * @property {string} path
 * @property {string} image
 * @property {string} name
 */

/**
 * @typedef {Object} TenorMediaFormat
 * @property {string} url
 * @property {number} duration
 * @property {string} preview
 * @property {number[]} dims
 * @property {number} size
 */

/**
 * @typedef {Object} TenorGif
 * @property {string} id
 * @property {string} title
 * @property {number} created
 * @property {string} content_description
 * @property {string} itemurl
 * @property {string} url
 * @property {string[]} tags
 * @property {string[]} flags
 * @property {boolean} hasaudio
 * @property {{ tinygif: TenorMediaFormat }} media_formats
 */

/**
 * @param {import("@web/core/utils/common/hooks").Ref} ref
 * @param {{ onSelected: function, className: String }} options
 */
export function useGifPicker(refName, options) {
    const ref = useRef(refName);
    const popover = usePopover(GifPicker, {
        position: "top",
        popoverClass: "o-fast-popover",
    });
    function toggle() {
        if (popover.isOpen) {
            popover.close();
        } else {
            popover.open(ref.el, options);
        }
    }
    return { toggle };
}

/**
 * @typedef {Object} Props
 * @property {function} onSelected Callback to use when the gif is selected
 * @property {string} [className]
 * @property {function} [close]
 * @extends {Component<Props, Env>}
 */
export class GifPicker extends Component {
    static template = "discuss.GifPicker";
    static props = ["onSelected", "className?", "close?"];

    setup() {
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.store = useStore();
        this.userService = useService("user");
        useAutofocus();
        useOnBottomScrolled(
            "scroller",
            () => {
                if (!this.state.showCategories) {
                    this.state.loadingGif = true;
                    if (!this.showFavorite) {
                        this.searchDebounced();
                    } else {
                        this.loadFavoritesDebounced(this.offset);
                    }
                }
            },
            300
        );
        this.next = "";
        this.showFavorite = false;
        this.offset = 0;
        this.state = useState({
            favorites: {
                /** @type {TenorGif[]} */
                gifs: [],
                offset: 0,
            },
            searchTerm: "",
            showCategories: true,
            /** @type {TenorCategory[]} */
            categories: [],
            loadingGif: false,
            loadingError: false,
            evenGif: {
                /** @type {TenorGif[]} */
                gifs: [],
                /** Size, in pixel, of the column. */
                columnSize: 0,
            },
            oddGif: {
                /** @type {TenorGif[]} */
                gifs: [],
                /** Size, in pixel, of the column. */
                columnSize: 0,
            },
        });
        this.searchDebounced = useDebounced(this.search, 200);
        this.loadFavoritesDebounced = useDebounced(this.loadFavorites, 200);
        onWillStart(() => {
            this.loadCategories();
        });
        if (!this.store.guest) {
            onWillStart(() => {
                this.loadFavorites();
            });
        }
    }

    async loadCategories() {
        try {
            const { tags } = await this.rpc(
                "/discuss/gif/categories",
                {
                    country: this.userService.lang.slice(3, 5),
                    locale: this.userService.lang,
                },
                { silent: true }
            );
            if (tags) {
                this.state.categories = tags;
            }
        } catch {
            this.state.loadingError = true;
        }
    }

    openCategories() {
        this.state.showCategories = true;
        this.state.searchTerm = "";
        this.clear();
    }

    closeCategories() {
        this.state.showCategories = false;
    }

    async search() {
        if (!this.state.searchTerm) {
            return;
        }
        this.state.loadingGif = true;
        try {
            const params = {
                country: this.userService.lang.slice(3, 5),
                locale: this.userService.lang,
                search_term: this.state.searchTerm,
            };
            if (this.next) {
                params.position = this.next;
            }
            const { results, next } = await this.rpc("/discuss/gif/search", params, {
                silent: true,
            });
            if (results) {
                this.next = next;
                for (const gif of results) {
                    this.pushGif(gif);
                }
            }
        } catch {
            this.state.loadingError = true;
        }
        this.state.loadingGif = false;
    }

    /**
     * @param {TenorGif} gif
     */
    pushGif(gif) {
        if (this.state.evenGif.columnSize <= this.state.oddGif.columnSize) {
            this.state.evenGif.gifs.push(gif);
            this.state.evenGif.columnSize += gif.media_formats.tinygif.dims[1];
        } else {
            this.state.oddGif.gifs.push(gif);
            this.state.oddGif.columnSize += gif.media_formats.tinygif.dims[1];
        }
    }

    onInput() {
        this.clear();
        this.state.loadingGif = true;
        this.searchDebounced();
        if (this.state.searchTerm) {
            this.closeCategories();
        } else {
            this.openCategories();
        }
    }

    onClick(ev) {
        markEventHandled(ev, "GifPicker.onClick");
    }

    /**
     * @param {TenorGif} gif
     */
    onClickGif(gif) {
        this.props.onSelected(gif);
        this.props.close();
    }

    clear() {
        this.state.evenGif.gifs = [];
        this.state.evenGif.columnSize = 0;
        this.state.oddGif.gifs = [];
        this.state.oddGif.columnSize = 0;
    }

    /**
     * @param {TenorCategory} category
     */
    async onClickCategory(category) {
        this.clear();
        this.state.searchTerm = category.searchterm;
        await this.search();
        this.closeCategories();
    }

    /**
     * @param {TenorGif} gif
     */
    async onClickFavorite(gif) {
        if (!this.isFavorite(gif)) {
            this.state.favorites.gifs.push(gif);
            await this.orm.silent.create("discuss.gif.favorite", [{ tenor_gif_id: gif.id }]);
        } else {
            removeFromArrayWithPredicate(this.state.favorites.gifs, ({ id }) => id === gif.id);
            await this.rpc(
                "/discuss/gif/remove_favorite",
                { tenor_gif_id: gif.id },
                { silent: true }
            );
        }
    }

    async loadFavorites() {
        this.state.loadingGif = true;
        const [results] = await this.rpc(
            "/discuss/gif/favorites",
            { offset: this.offset },
            { silent: true }
        );
        this.offset += 20;
        this.state.favorites.gifs.push(...results);
        for (const gif of results) {
            this.pushGif(gif);
        }
        this.state.loadingGif = false;
    }

    /**
     * @param {TenorGif} gif
     */
    isFavorite(gif) {
        return this.state.favorites.gifs.map((favorite) => favorite.id).includes(gif.id);
    }

    onClickFavoritesCategory() {
        this.showFavorite = true;
        for (const gif of this.state.favorites.gifs) {
            this.pushGif(gif);
        }
        this.closeCategories();
    }
}
