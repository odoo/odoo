odoo.define('web.Registry', function (require) {
"use strict";

var Class = require('web.Class');

/**
 * The registry is really pretty much only a mapping from some keys to some
 * values. The Registry class only add a few simple methods around that to make
 * it nicer and slightly safer.
 *
 * Note that registries have a fundamental problem: the value that you try to
 * get in a registry might not have been added yet, so of course, you need to
 * make sure that your dependencies are solid.  For this reason, it is a good
 * practice to avoid using the registry if you can simply import what you need
 * with the 'require' statement.
 *
 * However, on the flip side, sometimes you cannot just simply import something
 * because we would have a dependency cycle.  In that case, registries might
 * help.
 */
var Registry = Class.extend({
    /**
     * @constructor
     * @param {Object} [mapping] the initial data in the registry
     */
    init: function (mapping) {
        this.map = Object.create(mapping || null);
        this._scoreMapping = Object.create(null);
        this._sortedKeys = null;
        this.listeners = []; // listening callbacks on newly added items.
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Add a key (and a value) to the registry.
     *
     * Notify the listeners on newly added item in the registry.
     *
     * @param {string} key
     * @param {any} value
     * @param {number} [score] if given, this value will be used to order keys
     * @returns {Registry} can be used to chain add calls.
     */
    add: function (key, value, score) {
        this._scoreMapping[key] = score === undefined ? key : score;
        this._sortedKeys = null;
        this.map[key] = value;
        _.each(this.listeners, function (callback) {
            callback(key, value);
        });
        return this;
    },
    /**
     * Check if the registry contains the key
     *
     * @param {string} key
     * @returns {boolean}
     */
    contains: function (key) {
        return (key in this.map);
    },
    /**
     * Returns the content of the registry (an object mapping keys to values)
     *
     * @returns {Object}
     */
    entries: function () {
        return Object.create(this.map);
    },
    /**
     * Returns the value associated to the given key.
     *
     * @param {string} key
     * @returns {any}
     */
    get: function (key) {
        return this.map[key];
    },
    /**
     * Tries a number of keys, and returns the first object matching one of
     * the keys.
     *
     * @param {string[]} keys a sequence of keys to fetch the object for
     * @returns {any} the first result found matching an object
     */
    getAny: function (keys) {
        for (var i=0; i<keys.length; i++) {
            if (keys[i] in this.map) {
                return this.map[keys[i]];
            }
        }
        return null;
    },
    /**
     * Return the list of keys in map object.
     *
     * The registry guarantees that the keys have a consistent order, defined by
     * the 'score' value when the item has been added.
     *
     * @returns {string[]}
     */
    keys: function () {
        var self = this;
        if (!this._sortedKeys) {
            this._sortedKeys = _.sortBy(Object.keys(this.map), function (key) {
                return self._scoreMapping[key] || 0;
            });
        }
        return this._sortedKeys;
    },
    /**
     * Register a callback to execute when items are added to the registry.
     *
     * @param {function} callback function with parameters (key, value).
     */
    onAdd: function (callback) {
        this.listeners.push(callback);
    },
    /**
     * Return the list of values in map object
     *
     * @returns {string[]}
     */
    values: function () {
        var self = this;
        return this.keys().map(function (key) {
            return self.map[key];
        });
    },
});

return Registry;

});

