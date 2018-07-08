odoo.define('web.AbstractStorageService', function (require) {
'use strict';

/**
 * This module defines an abstraction for services that write into Storage
 * objects (e.g. localStorage or sessionStorage).
 */

var AbstractService = require('web.AbstractService');

var AbstractStorageService = AbstractService.extend({
    // the 'storage' attribute must be set by actual StorageServices extending
    // this abstraction
    storage: null,

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Removes all data from the storage
     */
    clear: function() {
        this.storage.clear();
    },
    /**
     * Returns the value associated with a given key in the storage
     *
     * @param {string} key
     * @returns {string}
     */
    getItem: function(key) {
        return this.storage.getItem(key);
    },
    /**
     * Removes the given key from the storage
     *
     * @param {string} key
     */
    removeItem: function(key) {
        this.storage.removeItem(key);
    },
    /**
     * Sets the value of a given key in the storage
     *
     * @param {string} key
     * @param {string} value
     */
    setItem: function(key, value) {
        this.storage.setItem(key,value);
    },
});

return AbstractStorageService;

});
