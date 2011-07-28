/*---------------------------------------------------------
 * OpenERP controller framework
 *--------------------------------------------------------*/

openerp.base.controller = function(instance) {
/**
 * John Resig Class with factory improvement
 */
(function() {
  var initializing = false, fnTest = /xyz/.test(function(){xyz;}) ? /\b_super\b/ : /.*/;
  // The base Class implementation (does nothing)
  this.Class = function(){};

  // Create a new Class that inherits from this class
  Class.extend = function(prop) {
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
        typeof _super[name] == "function" && fnTest.test(prop[name]) ?
        (function(name, fn){
          return function() {
            var tmp = this._super;

            // Add a new ._super() method that is the same method
            // but on the super-class
            this._super = _super[name];

            // The method only need to be bound temporarily, so we
            // remove it when we're done executing
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
      if ( !initializing && this.init ) {
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

// todo change john resig class to keep window clean
instance.base.Class = window.Class

instance.base.callback = function(obj, method) {
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
instance.base.generate_null_object_class = function(claz, add) {
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
    newer.init = instance.base.Controller.prototype.init;
    var tmpclass = claz.extend(newer);
    return tmpclass.extend(add || {});
};

// --------------------------------------------------------
// OLD 
// --------------------------------------------------------

/**
 * OpenERP Controller
 * TODO merge BaseWidget with Controller
 */
instance.base.Controller = instance.base.Class.extend( /** @lends instance.base.Controller# */{
    /**
     * @constructs
     * rpc operations, event binding and callback calling should be done in
     * start() instead of init so that events can be hooked in between.
     */
    init: function(parent, element_id) {
        this.element_id = element_id;
        this.$element = $('#' + element_id);
        if (element_id) {
            instance.screen[element_id] = this;
        }
        // save the parent children relationship
        this.controller_parent = parent;
        this.controller_children = [];
        if(parent && parent.controller_children) {
            parent.controller_children.push(this);
        }
        // backward compatibility
        this.parent = this.controller_parent;
        this.children = this.controller_children;

        // Transform on_* method into openerp.base.callbacks
        for (var name in this) {
            if(typeof(this[name]) == "function") {
                this[name].debug_name = name;
                // bind ALL function to this not only on_and _do ?
                if((/^on_|^do_/).test(name)) {
                    this[name] = instance.base.callback(this, this[name]);
                }
            }
        }
    },
    /**
     * Event binding, rpc and callback calling required to initialize the
     * object should happen here
     *
     * Returns a promise object letting callers (subclasses and direct callers)
     * know when this component is done starting
     *
     * @returns {jQuery.Deferred}
     */
    start: function() {
        // returns an already fulfilled promise. Maybe we could return nothing?
        // $.when can take non-deferred and in that case it simply considers
        // them all as fulfilled promises.
        // But in thise case we *have* to ensure callers use $.when and don't
        // try to call deferred methods on this return value.
        return $.Deferred().done().promise();
    },
    stop: function() {
        if (this.parent && this.parent.children) {
            this.parent.children = _.without(this.parent.children, this);
            this.parent.controller_children = this.parent.children;
        }
        this.parent = null;
        this.controller_parent = null;
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
 * OpenERP session aware controller
 * a controller takes an already existing dom element and manage it
 */
instance.base.Controller = instance.base.Controller.extend( /** @lends openerp.base.Controller# */{
    init: function(parent, element_id) {
        this._super(parent, element_id);
        if(this.controller_parent && this.controller_parent.session) {
            this.session = this.controller_parent.session;
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
    do_action: function(action, on_finished) {
        return this.parent.do_action(action, on_finished);
    }
});

/**
 * OpenERP session aware widget
 * A widget is a controller that doesnt take an element_id
 * it render its own html render() that you should insert into the dom
 * and bind it at start()
 */
instance.base.BaseWidget = instance.base.Controller.extend({
    /**
     * The name of the QWeb template that will be used for rendering. Must be
     * redefined in subclasses or the render() method can not be used.
     * 
     * @type string
     */
    template: null,
    /**
     * The prefix used to generate an id automatically. Should be redefined in
     * subclasses. If it is not defined, a default identifier will be used.
     * 
     * @type string
     */
    identifier_prefix: 'generic-identifier',
    /**
     * Base class for widgets. Handle rendering (based on a QWeb template),
     * identifier generation, parenting and destruction of the widget.
     * Also initialize the identifier.
     *
     * @constructs
     * @params {openerp.base.search.BaseWidget} parent The parent widget.
     */
    init: function (parent) {
        this._super(parent);
        this.make_id(this.identifier_prefix);
    },
    /**
     * Sets and returns a globally unique identifier for the widget.
     *
     * If a prefix is appended, the identifier will be appended to it.
     *
     * @params sections prefix sections, empty/falsy sections will be removed
     */
    make_id: function () {
        this.element_id = _.uniqueId(_.toArray(arguments).join('_'));
        return this.element_id;
    },
    /**
     * Render the widget. This.template must be defined.
     * The content of the current object is passed as context to the template.
     * 
     * @param {object} additional Additional context arguments to pass to the template.
     */
    render: function (additional) {
        return QWeb.render(this.template, _.extend({}, this, additional != null ? additional : {}));
    },
    /**
     * "Starts" the widgets. Called at the end of the rendering, this allows
     * to get a jQuery object referring to the DOM ($element attribute).
     */
    start: function () {
        this._super();
        var tmp = document.getElementById(this.element_id);
        this.$element = tmp ? $(tmp) : null;
    },
    /**
     * "Stops" the widgets. Called when the view destroys itself, this
     * lets the widgets clean up after themselves.
     */
    stop: function () {
        if(this.$element != null) {
            this.$element.remove();
        }
        this._super();
    }
});

// --------------------------------------------------------
// N-style aka New-Style or Niv-Style
// --------------------------------------------------------

instance.base.NivController = instance.base.Class.extend({
    init: function(parent) {
        this.controller_parent = parent;
        // Take the session of the parent if defined
        if(this.controller_parent && this.controller_parent.session) {
            this.session = this.controller_parent.session;
        }
        // Transform on_* method into openerp.base.callbacks
        for (var name in this) {
            if(typeof(this[name]) == "function") {
                this[name].debug_name = name;
                // bind ALL function to this not only on_and _do ?
                if((/^on_|^do_/).test(name)) {
                    this[name] = instance.base.callback(this, this[name]);
                }
            }
        }
    },
    /**
     * Event binding, rpc and callback calling required to initialize the
     * object should happen here
     *
     * Returns a promise object letting callers (subclasses and direct callers)
     * know when this component is done starting
     *
     * @returns {jQuery.Deferred}
     */
    start: function() {
        // returns an already fulfilled promise. Maybe we could return nothing?
        // $.when can take non-deferred and in that case it simply considers
        // them all as fulfilled promises.
        // But in thise case we *have* to ensure callers use $.when and don't
        // try to call deferred methods on this return value.
        return $.Deferred().done().promise();
    },
    stop: function() {
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
    do_action: function(action, on_finished) {
        return this.controller_parent.do_action(action, on_finished);
    }
});

instance.base.NivWidget = instance.base.Controller.extend({
    /**
     * The name of the QWeb template that will be used for rendering. Must be
     * redefined in subclasses or the render() method can not be used.
     * 
     * @type string
     */
    template: null,
    /**
     * The prefix used to generate an id automatically. Should be redefined in
     * subclasses. If it is not defined, a default identifier will be used.
     * 
     * @type string
     */
    identifier_prefix: 'generic-identifier',
    /**
     * Base class for widgets. Handle rendering (based on a QWeb template),
     * identifier generation, parenting and destruction of the widget.
     * Also initialize the identifier.
     *
     * @constructs
     * @params {openerp.base.search.BaseWidget} parent The parent widget.
     */
    init: function(parent, element_id) {
        this._super(parent);
        this.make_id(this.identifier_prefix);
        // this.element_id = element_id;
        // this.$element = $('#' + element_id);
        // if (element_id) {
        //     instance.screen[element_id] = this;
        // }
        // save the parent children relationship
        this.controller_children = [];
        if(parent && parent.controller_children) {
            parent.controller_children.push(this);
        }
        // backward compatibility
        this.parent = this.controller_parent;
        this.children = this.controller_children;

    },
    /**
     * Event binding, rpc and callback calling required to initialize the
     * object should happen here
     *
     * Returns a promise object letting callers (subclasses and direct callers)
     * know when this component is done starting
     *
     * @returns {jQuery.Deferred}
     */
    /**
     * "Starts" the widgets. Called at the end of the rendering, this allows
     * to get a jQuery object referring to the DOM ($element attribute).
     */
    start: function () {
        this._super();
        var tmp = document.getElementById(this.element_id);
        this.$element = tmp ? $(tmp) : null;
    },
    stop: function() {
        if(this.$element != null) {
            this.$element.remove();
        }
        if (this.parent && this.parent.children) {
            this.parent.children = _.without(this.parent.children, this);
            this.parent.controller_children = this.parent.children;
        }
        this.parent = null;
        this.controller_parent = null;
    },
    /**
     * Sets and returns a globally unique identifier for the widget.
     *
     * If a prefix is appended, the identifier will be appended to it.
     *
     * @params sections prefix sections, empty/falsy sections will be removed
     */
    make_id: function () {
        this.element_id = _.uniqueId(_.toArray(arguments).join('_'));
        return this.element_id;
    },
    /**
     * Render the widget. This.template must be defined.
     * The content of the current object is passed as context to the template.
     * 
     * @param {object} additional Additional context arguments to pass to the template.
     */
    render: function (additional) {
        return QWeb.render(this.template, _.extend({}, this, additional != null ? additional : {}));
    },
    widget_add: function(element, addfunc) {
    },
    widget_append: function(element) {
    },
    widget_prepend: function(element) {
    },
    widget_append2: function(element) {
    },
    widget_prepend2: function(element) {
    },
});


};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
