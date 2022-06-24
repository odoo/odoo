/** @odoo-module **/

import { registry } from '@web/core/registry';

export const unsplashService = {
    dependencies: ['rpc'],
    async start(env, { rpc }) {
        const _cache = {};
        return {
            async getImages(query, offset = 0, pageSize = 30) {
                const from = offset;
                const to = offset + pageSize;
                let cachedData = _cache[query];

                if (cachedData && (cachedData.images.length >= to || (cachedData.totalImages !== 0 && cachedData.totalImages < to))) {
                    return { images: cachedData.images.slice(from, to), isMaxed: to > cachedData.totalImages };
                }
                cachedData = await this._fetchImages(query);
                return { images: cachedData.images.slice(from, to), isMaxed: to > cachedData.totalImages };
            },
            /**
             * Fetches images from unsplash and stores it in cache
             */
            async _fetchImages(query) {
                if (!_cache[query]) {
                    _cache[query] = {
                        images: [],
                        maxPages: 0,
                        totalImages: 0,
                        pageCached: 0
                    };
                }
                const cachedData = _cache[query];
                const payload = {
                    query: query,
                    page: cachedData.pageCached + 1,
                    per_page: 30, // max size from unsplash API
                };
                const result = await rpc('/web_unsplash/fetch_images', payload);
                if (result.error) {
                    return Promise.reject(result.error);
                }
                cachedData.pageCached++;
                cachedData.images.push(...result.results);
                cachedData.maxPages = result.total_pages;
                cachedData.totalImages = result.total;
                return cachedData;
            },
        };
    },
};

registry.category('services').add('unsplash', unsplashService);
