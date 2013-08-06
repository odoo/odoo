/*
 * Copyright (c) 2012, OpenERP S.A.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
 * ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

openerp.web.corelib = function(instance) {

var ControllerMixin = {
    /**
     * Informs the action manager to do an action. This supposes that
     * the action manager can be found amongst the ancestors of the current widget.
     * If that's not the case this method will simply return `false`.
     */
    do_action: function() {
        var parent = this.getParent();
        if (parent) {
            return parent.do_action.apply(parent, arguments);
        }
        return false;
    },
    do_notify: function() {
        if (this.getParent()) {
            return this.getParent().do_notify.apply(this,arguments);
        }
        return false;
    },
    do_warn: function() {
        if (this.getParent()) {
            return this.getParent().do_warn.apply(this,arguments);
        }
        return false;
    },
    rpc: function(url, data, options) {
        return this.alive(openerp.session.rpc(url, data, options));
    }
};

/**
    A class containing common utility methods useful when working with OpenERP as well as the PropertiesMixin.
*/
openerp.web.Controller = openerp.web.Class.extend(openerp.web.PropertiesMixin, ControllerMixin, {
    /**
     * Constructs the object and sets its parent if a parent is given.
     *
     * @param {openerp.web.Controller} parent Binds the current instance to the given Controller instance.
     * When that controller is destroyed by calling destroy(), the current instance will be
     * destroyed too. Can be null.
     */
    init: function(parent) {
        openerp.web.PropertiesMixin.init.call(this);
        this.setParent(parent);
        this.session = openerp.session;
    },
});

openerp.web.Widget.include(_.extend({}, ControllerMixin, {
    init: function() {
        this._super.apply(this, arguments);
        this.session = openerp.session;
    },
}));

instance.web.Registry = instance.web.Class.extend({
    /**
     * Stores a mapping of arbitrary key (strings) to object paths (as strings
     * as well).
     *
     * Resolves those paths at query time in order to always fetch the correct
     * object, even if those objects have been overloaded/replaced after the
     * registry was created.
     *
     * An object path is simply a dotted name from the instance root to the
     * object pointed to (e.g. ``"instance.web.Session"`` for an OpenERP
     * session object).
     *
     * @constructs instance.web.Registry
     * @param {Object} mapping a mapping of keys to object-paths
     */
    init: function (mapping) {
        this.parent = null;
        this.map = mapping || {};
    },
    /**
     * Retrieves the object matching the provided key string.
     *
     * @param {String} key the key to fetch the object for
     * @param {Boolean} [silent_error=false] returns undefined if the key or object is not found, rather than throwing an exception
     * @returns {Class} the stored class, to initialize or null if not found
     */
    get_object: function (key, silent_error) {
        var path_string = this.map[key];
        if (path_string === undefined) {
            if (this.parent) {
                return this.parent.get_object(key, silent_error);
            }
            if (silent_error) { return void 'nooo'; }
            return null;
        }

        var object_match = instance;
        var path = path_string.split('.');
        // ignore first section
        for(var i=1; i<path.length; ++i) {
            object_match = object_match[path[i]];

            if (object_match === undefined) {
                if (silent_error) { return void 'noooooo'; }
                return null;
            }
        }
        return object_match;
    },
    /**
     * Checks if the registry contains an object mapping for this key.
     *
     * @param {String} key key to look for
     */
    contains: function (key) {
        if (key === undefined) { return false; }
        if (key in this.map) {
            return true;
        }
        if (this.parent) {
            return this.parent.contains(key);
        }
        return false;
    },
    /**
     * Tries a number of keys, and returns the first object matching one of
     * the keys.
     *
     * @param {Array} keys a sequence of keys to fetch the object for
     * @returns {Class} the first class found matching an object
     */
    get_any: function (keys) {
        for (var i=0; i<keys.length; ++i) {
            var key = keys[i];
            if (!this.contains(key)) {
                continue;
            }

            return this.get_object(key);
        }
        return null;
    },
    /**
     * Adds a new key and value to the registry.
     *
     * This method can be chained.
     *
     * @param {String} key
     * @param {String} object_path fully qualified dotted object path
     * @returns {instance.web.Registry} itself
     */
    add: function (key, object_path) {
        this.map[key] = object_path;
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
        var child = new instance.web.Registry(mapping);
        child.parent = this;
        return child;
    },
    /**
     * @deprecated use Registry#extend
     */
    clone: function (mapping) {
        console.warn('Registry#clone is deprecated, use Registry#extend');
        return this.extend(mapping);
    }
});

instance.web.py_eval = function(expr, context) {
    return py.eval(expr, _.extend({}, context || {}, {"true": true, "false": false, "null": null}));
};

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
