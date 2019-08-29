odoo.define('web.RamStorage', function (require) {
'use strict';

/**
 * This module defines an alternative of the Storage objects (localStorage,
 * sessionStorage), stored in RAM. It is used when those native Storage objects
 * are unavailable (e.g. in private browsing on Safari).
 */

var Class = require('web.Class');
var mixins = require('web.mixins');


var RamStorage = Class.extend(mixins.EventDispatcherMixin, {
    /**
     * @constructor
     */
    init: function () {
        mixins.EventDispatcherMixin.init.call(this);
        if (!this.storage) {
            this.clear();
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Removes all data from the storage
     */
    clear: function () {
        this.storage = Object.create(null);
        this.length = 0;
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
     * @param {integer} index
     * @return {string}
     */
    key: function (index) {
        return _.keys(this.storage)[index];
    },
    /**
     * Removes the given key from the storage
     *
     * @param {string} key
     */
    removeItem: function (key) {
        if (key in this.storage) {
            this.length--;
        }
        delete this.storage[key];
        this.trigger('storage', {key: key, newValue: null});
    },
    /**
     * Adds a given key-value pair to the storage, or update the value of the
     * given key if it already exists
     *
     * @param {string} key
     * @param {string} value
     */
    setItem: function (key, value) {
        if (!(key in this.storage)) {
            this.length++;
        }
        this.storage[key] = value;
        this.trigger('storage', {key: key, newValue: value});
    },
});

return RamStorage;

});
