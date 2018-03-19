odoo.define('web.RamStorage', function (require) {
'use strict';

/**
 * This module defines an alternative of the Storage objects (localStorage,
 * sessionStorage), stored in RAM. It is used when those native Storage objects
 * are unavailable (e.g. in private browsing on Safari).
 */

var Class = require('web.Class');

var RamStorage = Class.extend({
    /**
     * @constructor
     */
    init: function () {
        this.storage = Object.create(null);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Removes all data from the storage
     */
    clear: function () {
        this.init();
    },
    /**
     * Returns the value associated with a given key in the storage
     *
     * @param {string} key
     * @returns {string}
     */
    getItem: function (key) {
        return this.storage[key];
    },
    /**
     * Removes the given key from the storage
     *
     * @param {string} key
     */
    removeItem: function (key) {
        delete this.storage[key];
    },
    /**
     * Adds a given key-value pair to the storage, or update the value of the
     * given key if it already exists
     *
     * @param {string} key
     * @param {string} value
     */
    setItem: function (key, value) {
        this.storage[key] = value;
    },
});

return RamStorage;

});
