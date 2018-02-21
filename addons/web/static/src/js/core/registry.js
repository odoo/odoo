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
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Add a key (and a value) to the registry.
     *
     * @param {string} key
     * @param {any} value
     * @returns {Registry} can be used to chain add calls.
     */
    add: function (key, value) {
        this.map[key] = value;
        return this;
    },
    /**
     * Check if the registry contains the value
     *
     * @param {string} key
     * @returns {boolean}
     */
    contains: function (key) {
        return (key in this.map);
    },
    /**
     * Creates and returns a copy of the current mapping, with the provided
     * mapping argument added in (replacing existing keys if needed)
     *
     * Parent and child remain linked, a new key in the parent (which is not
     * overwritten by the child) will appear in the child.
     *
     * @param {Object} [mapping={}] a mapping of keys to object-paths
     */
    extend: function (mapping) {
        var child = new Registry(this.map);
        _.extend(child.map, mapping);
        return child;
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
});

return Registry;

});

