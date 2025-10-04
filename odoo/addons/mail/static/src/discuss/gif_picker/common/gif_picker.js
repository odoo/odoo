/* @odoo-module */

import { Component, onWillStart, useState, useEffect } from "@odoo/owl";
import { useOnBottomScrolled, useSequential } from "@mail/utils/common/hooks";

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
 * @typedef {Object} Props
 * @property {function} onSelect Callback to use when the gif is selected
 * @property {string} [className]
 * @property {function} [close]
 * @property {Object} [state]
 * @extends {Component<Props, Env>}
 */

export class GifPicker extends Component {
    static template = "discuss.GifPicker";
    static props = ["PICKERS?", "className?", "close?", "onSelect", "state?"];

    setup() {
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.store = useState(useService("mail.store"));
        this.userService = useService("user");
        this.sequential = useSequential();
        useAutofocus();
        useOnBottomScrolled(
            "scroller",
            () => {
                if (!this.state.showCategories) {
                    this.state.loadingGif = true;
                    if (!this.showFavorite) {
                        this.search();
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
                /** @type {Map<Number, TenorGif>} */
                gifs: new Map(),
                /** Size, in pixel, of the column. */
                columnSize: 0,
            },
            oddGif: {
                /** @type {Map<Number, TenorGif>} */
                gifs: new Map(),
                /** Size, in pixel, of the column. */
                columnSize: 0,
            },
        });
        this.loadFavoritesDebounced = useDebounced(this.loadFavorites, 200);
        onWillStart(() => {
            this.loadCategories();
        });
        if (!this.store.guest) {
            onWillStart(() => {
                this.loadFavorites();
            });
        }
        useEffect(
            () => {
                if (this.props.state?.picker !== this.props.PICKERS?.GIF) {
                    return;
                }
                this.clear();
                this.state.loadingGif = true;
                this.search();
                if (this.searchTerm) {
                    this.closeCategories();
                } else {
                    this.openCategories();
                }
            },
            () => [this.searchTerm, this.props.state?.picker]
        );
    }

    get style() {
        return "";
    }

    get searchTerm() {
        return this.props.state ? this.props.state.searchTerm : this.state.searchTerm;
    }

    set searchTerm(value) {
        if (this.props.state) {
            this.props.state.searchTerm = value;
        } else {
            this.state.searchTerm = value;
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
        this.showFavorite = false;
        this.state.showCategories = true;
        this.searchTerm = "";
        this.clear();
    }

    closeCategories() {
        this.state.showCategories = false;
    }

    async search() {
        if (!this.searchTerm) {
            return;
        }
        try {
            const params = {
                country: this.userService.lang.slice(3, 5),
                locale: this.userService.lang,
                search_term: this.searchTerm,
            };
            if (this.next) {
                params.position = this.next;
            }
            const res = await this.sequential(() => {
                this.state.loadingGif = true;
                const res = this.rpc("/discuss/gif/search", params, {
                    silent: true,
                });
                this.state.loadingGif = false;
                return res;
            });
            if (res) {
                const { next, results } = res;
                this.next = next;
                for (const gif of results) {
                    this.pushGif(gif);
                }
                this.state.loadingError = false;
            }
        } catch {
            this.state.loadingError = true;
        }
    }

    /**
     * @param {TenorGif} gif
     */
    pushGif(gif) {
        if (this.state.evenGif.columnSize <= this.state.oddGif.columnSize) {
            this.state.evenGif.gifs.set(gif.id, gif);
            this.state.evenGif.columnSize += gif.media_formats.tinygif.dims[1];
        } else {
            this.state.oddGif.gifs.set(gif.id, gif);
            this.state.oddGif.columnSize += gif.media_formats.tinygif.dims[1];
        }
    }

    /**
     * @param {TenorGif} gif
     */
    onClickGif(gif) {
        this.props.onSelect(gif, true);
        this.props.close?.();
    }

    clear() {
        this.state.evenGif.gifs.clear();
        this.state.evenGif.columnSize = 0;
        this.state.oddGif.gifs.clear();
        this.state.oddGif.columnSize = 0;
    }

    /**
     * @param {TenorCategory} category
     */
    async onClickCategory(category) {
        this.clear();
        this.props.state.searchTerm = category.searchterm;
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
            const index = this.state.favorites.gifs.findIndex(({ id }) => id === gif.id);
            if (index >= 0) {
                this.state.favorites.gifs.splice(index, 1);
            }
            await this.rpc(
                "/discuss/gif/remove_favorite",
                { tenor_gif_id: gif.id },
                { silent: true }
            );
        }
    }

    async loadFavorites() {
        this.state.loadingGif = true;
        try {
            const [results] = await this.rpc(
                "/discuss/gif/favorites",
                { offset: this.offset },
                { silent: true }
            );
            this.offset += 20;
            this.state.favorites.gifs.push(...results);
        } catch {
            this.state.loadingError = true;
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
