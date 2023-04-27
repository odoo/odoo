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

    /**
     * @override
     */
    destroy: function () {
        // storage can be permanent or transient, destroy transient ones
        if ((this.storage || {}).destroy) {
            this.storage.destroy();
        }
        this._super.apply(this, arguments);
    },

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
    getItem: function(key, defaultValue) {
        var val = this.storage.getItem(key);
        return val ? JSON.parse(val) : defaultValue;
    },
    /**
     * @param {integer} index
     * @return {string}
     */
    key: function (index) {
        return this.storage.key(index);
    },
    /**
     * @return {integer}
     */
    length: function () {
        return this.storage.length;
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
        this.storage.setItem(key, JSON.stringify(value));
    },
    /**
     * Add an handler on storage event
     *
     */
    onStorage: function () {
        this.storage.on.apply(this.storage, ["storage"].concat(Array.prototype.slice.call(arguments)));
    },
});

return AbstractStorageService;

});
