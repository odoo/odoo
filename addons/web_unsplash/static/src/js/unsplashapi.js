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
     * @param {Integer} pageNumber page number to retrieve
     */
    getImages: function (query, pageSize, pageNumber) {
        var self = this;
        var to = pageSize * pageNumber;
        var from = to - pageSize;
        var cachedData = this._cache[query];

        if (cachedData && (cachedData.images.length >= to || (cachedData.totalImages !== 0 && cachedData.totalImages < to))) {
            return $.when({ images: cachedData.images.slice(from, to), isMaxed: to > cachedData.totalImages });
        }
        return this._getAPIKey().then(function (clientID) {
            if (!clientID) {
                return $.Deferred().reject({ key_not_found: true });
            }
            return self._fetchImages(query).then(function (cachedData) {
                return { images: cachedData.images.slice(from, to), isMaxed: to > cachedData.totalImages };
            });
        });
    },
    /**
     * Notifies Unsplash from an image download. (API requirement)
     *
     * @param {String} url url of the image to notify
     */
    notifyDownload: function (url) {
        $.get(url, { client_id: this.clientId });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Checks and retrieves the unsplash API key
     *
     * @private
     */
    _getAPIKey: function () {
        var self = this;
        if (this.clientId) {
            return $.Deferred().resolve(self.clientId);
        }
        return this._rpc({
            route: '/web_unsplash/get_client_id',
        }).then(function (res) {
            self.clientId = res;
            return res;
        });
    },
    /**
     * Fetches images from unsplash and stores it in cache
     *
     * @param {String} query search terms
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
            client_id: this.clientId,
            per_page: 30, // max size from unsplash API
        };
        return $.get('https://api.unsplash.com/search/photos/', payload).then(function (result) {
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
