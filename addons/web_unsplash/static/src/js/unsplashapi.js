odoo.define('unsplash.api', function (require) {
'use strict';

var Class = require('web.Class');
var rpc = require('web.rpc');
var Mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');

var UnsplashCore = Class.extend(Mixins.EventDispatcherMixin, ServicesMixin, {
    /**
     * @constructor
     */
    init: function (parent) {
        Mixins.EventDispatcherMixin.init.call(this, arguments);
        this.setParent(parent);

        this._cache = {};
        this.clientId = false;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Gets unsplash images from query string.
     *
     * @param {String} query search terms
     * @param {Integer} pageSize number of image to display per page
     * @returns {Promise}
     */
    getImages: function (query, pageSize) {
        var from = 0;
        var to = pageSize;
        var cachedData = this._cache[query];

        if (cachedData && (cachedData.images.length >= to || (cachedData.totalImages !== 0 && cachedData.totalImages < to))) {
            return Promise.resolve({ images: cachedData.images.slice(from, to), isMaxed: to > cachedData.totalImages });
        }
        return this._fetchImages(query).then(function (cachedData) {
            return { images: cachedData.images.slice(from, to), isMaxed: to > cachedData.totalImages };
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Fetches images from unsplash and stores it in cache
     *
     * @param {String} query search terms
     * @returns {Promise}
     * @private
     */
    _fetchImages: function (query) {
        if (!this._cache[query]) {
            this._cache[query] = {
                images: [],
                maxPages: 0,
                totalImages: 0,
                pageCached: 0
            };
        }
        var cachedData = this._cache[query];
        var payload = {
            query: query,
            page: cachedData.pageCached + 1,
            per_page: 30, // max size from unsplash API
        };
        return this._rpc({
            route: '/web_unsplash/fetch_images',
            params: payload,
        }).then(function (result) {
            if (result.error) {
                return Promise.reject(result.error);
            }
            cachedData.pageCached++;
            cachedData.images.push.apply(cachedData.images, result.results);
            cachedData.maxPages = result.total_pages;
            cachedData.totalImages = result.total;
            return cachedData;
        });
    },
});

return UnsplashCore;

});
