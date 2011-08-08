/*---------------------------------------------------------
 * OpenERP controller framework
 *--------------------------------------------------------*/

openerp.base.core = function(openerp) {
/**
 * John Resig Class with factory improvement
 */
(function() {
    var initializing = false,
        fnTest = /xyz/.test(function(){xyz;}) ? /\b_super\b/ : /.*/;
    // The base Class implementation (does nothing)
    openerp.base.Class = function(){};

    // Create a new Class that inherits from this class
    openerp.base.Class.extend = function(prop) {
        var _super = this.prototype;

        // Instantiate a base class (but only create the instance,
        // don't run the init constructor)
        initializing = true;
        var prototype = new this();
        initializing = false;

        // Copy the properties over onto the new prototype
        for (var name in prop) {
            // Check if we're overwriting an existing function
            prototype[name] = typeof prop[name] == "function" &&
                              typeof _super[name] == "function" &&
                              fnTest.test(prop[name]) ?
                    (function(name, fn) {
                        return function() {
                            var tmp = this._super;

                            // Add a new ._super() method that is the same
                            // method but on the super-class
                            this._super = _super[name];

                            // The method only need to be bound temporarily, so
                            // we remove it when we're done executing
                            var ret = fn.apply(this, arguments);
                            this._super = tmp;

                            return ret;
                        };
                    })(name, prop[name]) :
                    prop[name];
        }

        // The dummy class constructor
        function Class() {
            // All construction is actually done in the init method
            if (!initializing && this.init) {
                var ret = this.init.apply(this, arguments);
                if (ret) { return ret; }
            }
            return this;
        }

        // Populate our constructed prototype object
        Class.prototype = prototype;

        // Enforce the constructor to be what we expect
        Class.constructor = Class;

        // And make this class extendable
        Class.extend = arguments.callee;

        return Class;
    };
})();

openerp.base.callback = function(obj, method) {
    var callback = function() {
        var args = Array.prototype.slice.call(arguments);
        var r;
        for(var i = 0; i < callback.callback_chain.length; i++)  {
            var c = callback.callback_chain[i];
            if(c.unique) {
                callback.callback_chain.splice(i, 1);
                i -= 1;
            }
            r = c.callback.apply(c.self, c.args.concat(args));
            // TODO special value to stop the chain
            // openerp.base.callback_stop
        }
        return r;
    };
    callback.callback_chain = [];
    callback.add = function(f) {
        if(typeof(f) == 'function') {
            f = { callback: f, args: Array.prototype.slice.call(arguments, 1) };
        }
        f.self = f.self || null;
        f.args = f.args || [];
        f.unique = !!f.unique;
        if(f.position == 'last') {
            callback.callback_chain.push(f);
        } else {
            callback.callback_chain.unshift(f);
        }
        return callback;
    };
    callback.add_first = function(f) {
        return callback.add.apply(null,arguments);
    };
    callback.add_last = function(f) {
        return callback.add({
            callback: f,
            args: Array.prototype.slice.call(arguments, 1),
            position: "last"
        });
    };

    return callback.add({
        callback: method,
        self:obj,
        args:Array.prototype.slice.call(arguments, 2)
    });
};

/**
 * Generates an inherited class that replaces all the methods by null methods (methods
 * that does nothing and always return undefined).
 *
 * @param {Class} claz
 * @param {dict} add Additional functions to override.
 * @return {Class}
 */
openerp.base.generate_null_object_class = function(claz, add) {
    var newer = {};
    var copy_proto = function(prototype) {
        for (var name in prototype) {
            if(typeof prototype[name] == "function") {
                newer[name] = function() {};
            }
        }
        if (prototype.prototype)
            copy_proto(prototype.prototype);
    };
    copy_proto(claz.prototype);
    newer.init = openerp.base.Widget.prototype.init;
    var tmpclass = claz.extend(newer);
    return tmpclass.extend(add || {});
};

/**
 * Base error for lookup failure
 *
 * @class
 */
openerp.base.NotFound = openerp.base.Class.extend( /** @lends openerp.base.NotFound# */ {
});
openerp.base.KeyNotFound = openerp.base.NotFound.extend( /** @lends openerp.base.KeyNotFound# */ {
    /**
     * Thrown when a key could not be found in a mapping
     *
     * @constructs
     * @extends openerp.base.NotFound
     * @param {String} key the key which could not be found
     */
    init: function (key) {
        this.key = key;
    },
    toString: function () {
        return "The key " + this.key + " was not found";
    }
});
openerp.base.ObjectNotFound = openerp.base.NotFound.extend( /** @lends openerp.base.ObjectNotFound# */ {
    /**
     * Thrown when an object path does not designate a valid class or object
     * in the openerp hierarchy.
     *
     * @constructs
     * @extends openerp.base.NotFound
     * @param {String} path the invalid object path
     */
    init: function (path) {
        this.path = path;
    },
    toString: function () {
        return "Could not find any object of path " + this.path;
    }
});
openerp.base.Registry = openerp.base.Class.extend( /** @lends openerp.base.Registry# */ {
    /**
     * Stores a mapping of arbitrary key (strings) to object paths (as strings
     * as well).
     *
     * Resolves those paths at query time in order to always fetch the correct
     * object, even if those objects have been overloaded/replaced after the
     * registry was created.
     *
     * An object path is simply a dotted name from the openerp root to the
     * object pointed to (e.g. ``"openerp.base.Session"`` for an OpenERP
     * session object).
     *
     * @constructs
     * @param {Object} mapping a mapping of keys to object-paths
     */
    init: function (mapping) {
        this.map = mapping || {};
    },
    /**
     * Retrieves the object matching the provided key string.
     *
     * @param {String} key the key to fetch the object for
     * @returns {Class} the stored class, to initialize
     *
     * @throws {openerp.base.KeyNotFound} if the object was not in the mapping
     * @throws {openerp.base.ObjectNotFound} if the object path was invalid
     */
    get_object: function (key) {
        var path_string = this.map[key];
        if (path_string === undefined) {
            throw new openerp.base.KeyNotFound(key);
        }

        var object_match = openerp;
        var path = path_string.split('.');
        // ignore first section
        for(var i=1; i<path.length; ++i) {
            object_match = object_match[path[i]];

            if (object_match === undefined) {
                throw new openerp.base.ObjectNotFound(path_string);
            }
        }
        return object_match;
    },
    /**
     * Tries a number of keys, and returns the first object matching one of
     * the keys.
     *
     * @param {Array} keys a sequence of keys to fetch the object for
     * @returns {Class} the first class found matching an object
     *
     * @throws {openerp.base.KeyNotFound} if none of the keys was in the mapping
     * @trows {openerp.base.ObjectNotFound} if a found object path was invalid
     */
    get_any: function (keys) {
        for (var i=0; i<keys.length; ++i) {
            try {
                return this.get_object(keys[i]);
            } catch (e) {
                if (e instanceof openerp.base.KeyNotFound) {
                    continue;
                }
                throw e;
            }
        }
        throw new openerp.base.KeyNotFound(keys.join(','));
    },
    /**
     * Adds a new key and value to the registry.
     *
     * This method can be chained.
     *
     * @param {String} key
     * @param {String} object_path fully qualified dotted object path
     * @returns {openerp.base.Registry} itself
     */
    add: function (key, object_path) {
        this.map[key] = object_path;
        return this;
    },
    /**
     * Creates and returns a copy of the current mapping, with the provided
     * mapping argument added in (replacing existing keys if needed)
     *
     * @param {Object} [mapping={}] a mapping of keys to object-paths
     */
    clone: function (mapping) {
        return new openerp.base.Registry(
            _.extend({}, this.map, mapping || {}));
    }
});

/**
 * Utility class that any class is allowed to extend to easy common manipulations.
 *
 * It provides rpc calls, callback on all methods preceded by "on_" or "do_" and a
 * logging facility.
 */
openerp.base.SessionAware = openerp.base.Class.extend({
    init: function(session) {
        this.session = session;

        // Transform on_* method into openerp.base.callbacks
        for (var name in this) {
            if(typeof(this[name]) == "function") {
                this[name].debug_name = name;
                // bind ALL function to this not only on_and _do ?
                if((/^on_|^do_/).test(name)) {
                    this[name] = openerp.base.callback(this, this[name]);
                }
            }
        }
    },
    /**
     * Performs a JSON-RPC call
     *
     * @param {String} url endpoint url
     * @param {Object} data RPC parameters
     * @param {Function} success RPC call success callback
     * @param {Function} error RPC call error callback
     * @returns {jQuery.Deferred} deferred object for the RPC call
     */
    rpc: function(url, data, success, error) {
        return this.session.rpc(url, data, success, error);
    },
    log: function() {
        var args = Array.prototype.slice.call(arguments);
        var caller = arguments.callee.caller;
        // TODO add support for line number using
        // https://github.com/emwendelin/javascript-stacktrace/blob/master/stacktrace.js
        // args.unshift("" + caller.debug_name);
        this.on_log.apply(this,args);
    },
    on_log: function() {
        if(window.openerp.debug || (window.location.search.indexOf('?debug') !== -1)) {
            var notify = false;
            var body = false;
            if(window.console) {
                console.log(arguments);
            } else {
                body = true;
            }
            var a = Array.prototype.slice.call(arguments, 0);
            for(var i = 0; i < a.length; i++) {
                var v = a[i]==null ? "null" : a[i].toString();
                if(i==0) {
                    notify = v.match(/^not/);
                    body = v.match(/^bod/);
                }
                if(body) {
                    $('<pre></pre>').text(v).appendTo($('body'));
                }
                if(notify && this.notification) {
                    this.notification.notify("Logging:",v);
                }
            }
        }
    }
});

/**
 * Base class for all visual components. Provides a lot of functionalities helpful
 * for the management of a part of the DOM.
 *
 * Widget handles:
 * - Rendering with QWeb.
 * - Life-cycle management and parenting (when a parent is destroyed, all its children are
 *     destroyed too).
 * - Insertion in DOM.
 *
 * Widget also extends SessionAware for ease of use.
 *
 * Guide to create implementations of the Widget class:
 * ==============================================
 *
 * Here is a sample child class:
 *
 * MyWidget = openerp.base.Widget.extend({
 *     // the name of the QWeb template to use for rendering
 *     template: "MyQWebTemplate",
 *     // identifier prefix, it is useful to put an obvious one for debugging
 *     identifier_prefix: 'my-id-prefix-',
 *
 *     init: function(parent) {
 *         this._super(parent);
 *         // stuff that you want to init before the rendering
 *     },
 *     start: function() {
 *         this._super();
 *         // stuff you want to make after the rendering, `this.$element` holds a correct value
 *         this.$element.find(".my_button").click(/* an example of event binding * /);
 *
 *         // if you have some asynchronous operations, it's a good idea to return
 *         // a promise in start()
 *         var promise = this.rpc(...);
 *         return promise;
 *     }
 * });
 *
 * Now this class can simply be used with the following syntax:
 *
 * var my_widget = new MyWidget(this);
 * my_widget.appendTo($(".some-div"));
 *
 * With these two lines, the MyWidget instance was inited, rendered, it was inserted into the
 * DOM inside the ".some-div" div and its events were binded.
 *
 * And of course, when you don't need that widget anymore, just do:
 *
 * my_widget.stop();
 *
 * That will kill the widget in a clean way and erase its content from the dom.
 */
openerp.base.Widget = openerp.base.SessionAware.extend({
    /**
     * The name of the QWeb template that will be used for rendering. Must be
     * redefined in subclasses or the default render() method can not be used.
     *
     * @type string
     */
    template: null,
    /**
     * The prefix used to generate an id automatically. Should be redefined in
     * subclasses. If it is not defined, a generic identifier will be used.
     *
     * @type string
     */
    identifier_prefix: 'generic-identifier-',
    /**
     * Construct the widget and set its parent if a parent is given.
     *
     * @constructs
     * @param {openerp.base.Widget} parent Binds the current instance to the given Widget instance.
     * When that widget is destroyed by calling stop(), the current instance will be
     * destroyed too. Can be null.
     * @param {String} element_id Deprecated. Sets the element_id. Only useful when you want
     * to bind the current Widget to an already existing part of the DOM, which is not compatible
     * with the DOM insertion methods provided by the current implementation of Widget. So
     * for new components this argument should not be provided any more.
     */
    init: function(parent, /** @deprecated */ element_id) {
        this._super((parent || {}).session);
        // if given an element_id, try to get the associated DOM element and save
        // a reference in this.$element. Else just generate a unique identifier.
        this.element_id = element_id;
        this.element_id = this.element_id || _.uniqueId(this.identifier_prefix);
        var tmp = document.getElementById(this.element_id);
        this.$element = tmp ? $(tmp) : undefined;

        this.widget_parent = parent;
        this.widget_children = [];
        if(parent && parent.widget_children) {
            parent.widget_children.push(this);
        }
        // useful to know if the widget was destroyed and should not be used anymore
        this.widget_is_stopped = false;
    },
    /**
     * Render the current widget and appends it to the given jQuery object or Widget.
     *
     * @param target A jQuery object or a Widget instance.
     */
    appendTo: function(target) {
        var self = this;
        return this._render_and_insert(function(t) {
            self.$element.appendTo(t);
        }, target);
    },
    /**
     * Render the current widget and prepends it to the given jQuery object or Widget.
     *
     * @param target A jQuery object or a Widget instance.
     */
    prependTo: function(target) {
        var self = this;
        return this._render_and_insert(function(t) {
            self.$element.prependTo(t);
        }, target);
    },
    /**
     * Render the current widget and inserts it after to the given jQuery object or Widget.
     *
     * @param target A jQuery object or a Widget instance.
     */
    insertAfter: function(target) {
        var self = this;
        return this._render_and_insert(function(t) {
            self.$element.insertAfter(t);
        }, target);
    },
    /**
     * Render the current widget and inserts it before to the given jQuery object or Widget.
     *
     * @param target A jQuery object or a Widget instance.
     */
    insertBefore: function(target) {
        var self = this;
        return this._render_and_insert(function(t) {
            self.$element.insertBefore(t);
        }, target);
    },
    _render_and_insert: function(insertion, target) {
        var rendered = this.render();
        this.$element = $(rendered);
        if (target instanceof openerp.base.Widget)
            target = target.$element;
        insertion(target);
        return this.start();
    },
    /**
     * Renders the widget using QWeb, `this.template` must be defined.
     * The context given to QWeb contains the "widget" key that references `this`.
     *
     * @param {Object} additional Additional context arguments to pass to the template.
     */
    render: function (additional) {
        return QWeb.render(this.template, _.extend({widget: this}, additional || {}));
    },
    /**
     * Method called after rendering. Mostly used to bind actions, perform asynchronous
     * calls, etc...
     *
     * By convention, the method should return a promise to inform the caller when
     * this widget has been initialized.
     *
     * @returns {jQuery.Deferred}
     */
    start: function() {
        if (!this.$element) {
            var tmp = document.getElementById(this.element_id);
            this.$element = tmp ? $(tmp) : undefined;
        }
        return $.Deferred().done().promise();
    },
    /**
     * Destroys the current widget, also destory all its children before destroying itself.
     */
    stop: function() {
        _.each(_.clone(this.widget_children), function(el) {
            el.stop();
        });
        if(this.$element != null) {
            this.$element.remove();
        }
        if (this.widget_parent && this.widget_parent.widget_children) {
            this.widget_parent.widget_children = _.without(this.widget_parent.widget_children, this);
        }
        this.widget_parent = null;
        this.widget_is_stopped = true;
    },
    /**
     * Inform the action manager to do an action. Of course, this suppose that
     * the action manager can be found amongst the ancestors of the current widget.
     * If that's not the case this method will simply return `false`.
     */
    do_action: function(action, on_finished) {
        if (this.widget_parent) {
            return this.widget_parent.do_action(action, on_finished);
        }
        return false;
    },
    rpc: function(url, data, success, error) {
        var def = $.Deferred().then(success, error);
        var self = this;
        this._super(url, data). then(function() {
            if (!self.widget_is_stopped)
                def.resolve.apply(def, arguments);
        }, function() {
            if (!self.widget_is_stopped)
                def.reject.apply(def, arguments);
        });
        return def.promise();
    }
});

/**
 * @deprecated
 * For retro compatibility only, the only difference with is that render() uses
 * directly `this` instead of context with a "widget" key.
 */
openerp.base.OldWidget = openerp.base.Widget.extend({
    render: function (additional) {
        return QWeb.render(this.template, _.extend(_.extend({}, this), additional || {}));
    }
});

};
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
