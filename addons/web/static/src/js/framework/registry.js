odoo.define('web.Registry', function (require) {
"use strict";

var Class = require('web.Class');

var Registry = Class.extend({
    init: function (mapping) {
        this.map = Object.create(mapping || null);
    },
    get: function (key) {
        return this.map[key];
    },
    contains: function (key) {
        return (key in this.map);
    },
    /**
     * Tries a number of keys, and returns the first object matching one of
     * the keys.
     *
     * @param {Array} keys a sequence of keys to fetch the object for
     * @returns {Class} the first class found matching an object
     */
    get_any: function (keys) {
        for (var i=0; i<keys.length; i++) {
            if (keys[i] in this.map) {
                return this.map[keys[i]];
            }
        }
        return null;
    },
    add: function (key, value) {
        this.map[key] = value;
        return this;
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
});

return Registry;

});

