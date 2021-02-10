/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one, one2many } from '@mail/model/model_field';
import { clear, link } from '@mail/model/model_field_command';

function factory(dependencies) {

    class GifManager extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Initialize the gif manager data
         */
        init() {
            this.getCategories();
            this.getFavorite();
        }

        /**
         * Fetch tenor current categories.
         */
        async getCategories() {
            this.update({ categories: clear() });
            // Special category: favorites gif linked first
            const favorites = this.env.models['mail.gif_category'].insert({
                title: '#Favorite',
                type: 'favorite',
            });
            this.update({ categories: link(favorites) });
            // Get the categories from tenor and link them
            const categoriesFromTenor = await this._ajax('categories');
            for (const category of categoriesFromTenor.tags) {
                const gifCategory = this.env.models['mail.gif_category'].insert({
                    title: category.name,
                    url: category.image,
                    image: category.image,
                    type: 'category',
                    searchTerm: category.searchterm,
                });
                this.update({ categories: link(gifCategory) });
            }
        }

        /**
         * Fetch the user favorites gifs and link them to the model manager.
         */
        async getFavorite() {
            this.update({ favorites: clear() });
            const favorites = await this.env.services.rpc({
                route: '/mail/get_gif_favorites',
            });
            if (!favorites.results) {
                return;
            }
            // Ask the gif list to tenor
            const ids = favorites.results.map(fav => fav.gif_id).join(',');
            this.update({
                nextFavorite: favorites.offset
            });
            const response = await this._ajax('gifs', { ids });
            for (const search of response.results) {
                const gif = this.env.models['mail.gif'].insert({
                    gifManager: link(this),
                    title: search.title,
                    url: search.itemurl,
                    image: search.media[0].mediumgif.url,
                    type: 'favorites',
                    id: search.id,
                });
                this.update({ favorites: link(gif) });
            }
        }

        async favoriteMore() {
            this.update({
                isLoadingMore: true,
            });
            const favorites = await this.env.services.rpc({
                route: '/mail/get_gif_favorites',
                params: {
                    offset: this.nextFavorite
                }
            });
            if (!favorites.results) {
                return;
            }
            // Ask the gif list to tenor
            const ids = favorites.results.map(fav => fav.gif_id).join(',');
            this.update({
                nextFavorite: favorites.offset
            });
            const response = await this._ajax('gifs', { ids });
            for (const search of response.results) {
                const gif = this.env.models['mail.gif'].insert({
                    gifManager: link(this),
                    title: search.title,
                    url: search.itemurl,
                    image: search.media[0].mediumgif.url,
                    type: 'favorites',
                    id: search.id,
                });
                this.update({ favorites: link(gif) });
            }
            this.update({
                isLoadingMore: false,
            });
        }

        /**
         * Perform a search on tenor API.
         * @param {String} search the search term
         */
        async search(searchTerm) {
            this.update({ searchInputContent: searchTerm });
            if (!searchTerm) {
                this.update({ active: 'categories' });
            } else {
                this.update({
                    searchInputContent: searchTerm,
                    active: 'search',
                    searchGifs: clear(),
                });
                const response = await this._ajax('search', { q: searchTerm });
                this.update({ next: response.next });
                for (const searchResult of response.results) {
                    const gif = this.env.models['mail.gif'].insert({
                        gifManager: link(this),
                        title: searchResult.title,
                        url: searchResult.itemurl,
                        image: searchResult.media[0].mediumgif.url,
                        type: 'gif',
                        id: searchResult.id,
                    });
                    this.update({ searchGifs: link(gif) });
                }
            }
        }

        async searchMore() {
            this.update({
                isLoadingMore: true,
            });
            const response = await this._ajax('search', { q: this.searchInputContent, pos: this.next });
            this.update({ next: response.next });
            for (const searchResult of response.results) {
                const gif = this.env.models['mail.gif'].insert({
                    gifManager: link(this),
                    title: searchResult.title,
                    url: searchResult.itemurl,
                    image: searchResult.media[0].mediumgif.url,
                    type: 'gif',
                    id: searchResult.id,
                });
                this.update({ searchGifs: link(gif) });
            }
            this.update({
                isLoadingMore: false,
            });
        }

        /**
         * Insert a gif url inside the composer.
         */
        insertGif(gif) {
            this.composer.update({
                textInputContent: this.composer.textInputContent + ' ' + decodeURI(gif.url)
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        async _ajax(endpoint, params = {}) {
            const _params = new URLSearchParams(params);
            _params.append('key', this.env.messaging.tenorApiKey);
            _params.append('locale', this.env.messaging.locale.language);
            const stringParams = '?' + _params.toString();
            const response = await this.env.browser.fetch('https://g.tenor.com/v1/' + endpoint + stringParams);
            return response.json();
        }

        _computeGifs() {
            return link(this.favorites.concat(this.searchGifs));
        }

    }

    GifManager.fields = {
        /**
         * Determine the active view in the gif manager.
         */
        active: attr({
            default: 'categories',
        }),
        /**
         * Contain the current categories from tenor.
         */
        categories: one2many('mail.gif_category', {
            default: [],
            inverse: 'gifManager',
        }),
        /**
         * Link between the composer and his gif manager.
         */
        composer: one2one('mail.composer', {
            inverse: 'gifManager',
        }),
        /**
         * Contain user favorite gifs.
         */
        favorites: one2many('mail.gif', {
            default: [],
        }),
        /**
         * Dertermine all the gifs inside this manager.
         */
        gifs: one2many('mail.gif', {
            compute: '_computeGifs',
            dependencies: [
                'searchGifs',
                'favorites',
            ],
            inverse: 'gifManager',
        }),
        /**
         * Define if we are loading new gif inside the view.
         */
        isLoadingMore: attr({
            default: false,
        }),
        next: attr(),
        nextFavorite: attr(),
        /**
         * Contain the result of the gif search.
         */
        searchGifs: one2many('mail.gif', {
            default: [],
        }),
        /**
         * Contain the search term.
         */
        searchInputContent: attr({
            default: '',
        }),
    };

    GifManager.modelName = 'mail.gif_manager';

    return GifManager;
}

registerNewModel('mail.gif_manager', factory);
