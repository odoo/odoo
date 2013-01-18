/*
Copyright (c) 2012, Nicolas Vanhoren
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met: 

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer. 
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution. 

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

(function() {

if (typeof(define) !== "undefined") { // requirejs
    define(["jquery", "underscore"], nova_declare);
} else if (typeof(exports) !== "undefined") { // node
    var _ = require("underscore")
    _.extend(exports, nova_declare(null, _));
} else { // define global variable 'nova'
    nova = nova_declare($, _);
}

function nova_declare($, _) {
    var nova = {};
    nova.internal = {};

    /*
     * Modified Armin Ronacher's Classy library.
     *
     * Defines The Class object. That object can be used to define and inherit classes using
     * the $extend() method.
     *
     * Example:
     *
     * var Person = nova.Class.$extend({
     *  __init__: function(isDancing){
     *     this.dancing = isDancing;
     *   },
     *   dance: function(){
     *     return this.dancing;
     *   }
     * });
     *
     * The __init__() method act as a constructor. This class can be instancied this way:
     *
     * var person = new Person(true);
     * person.dance();
     *
     * The Person class can also be extended again:
     *
     * var Ninja = Person.$extend({
     *   __init__: function(){
     *     this.$super( false );
     *   },
     *   dance: function(){
     *     // Call the inherited version of dance()
     *     return this.$super();
     *   },
     *   swingSword: function(){
     *     return true;
     *   }
     * });
     *
     * When extending a class, each re-defined method can use this.$super() to call the previous
     * implementation of that method.
     */
    /**
    * Classy - classy classes for JavaScript
    *
    * :copyright: (c) 2011 by Armin Ronacher. 
    * :license: BSD.
    */
    (function(){
        var
            context = this,
            disable_constructor = false;

        /* we check if $super is in use by a class if we can.  But first we have to
         check if the JavaScript interpreter supports that.  This also matches
         to false positives later, but that does not do any harm besides slightly
         slowing calls down. */
        var probe_super = (function(){this.$super();}).toString().indexOf('$super') > 0;
        function usesSuper(obj) {
            return !probe_super || /\B\$super\b/.test(obj.toString());
        }

        /* helper function to set the attribute of something to a value or
         removes it if the value is undefined. */
        function setOrUnset(obj, key, value) {
            if (value === undefined)
                delete obj[key];
            else
                obj[key] = value;
        }

        /* gets the own property of an object */
        function getOwnProperty(obj, name) {
            return Object.prototype.hasOwnProperty.call(obj, name)
                ? obj[name] : undefined;
        }

        /* instanciate a class without calling the constructor */
        function cheapNew(cls) {
            disable_constructor = true;
            var rv = new cls;
            disable_constructor = false;
            return rv;
        }

        /* the base class we export */
        var Class = function() {};

        /* extend functionality */
        Class.$extend = function(properties) {
            var super_prototype = this.prototype;

            /* disable constructors and instanciate prototype.  Because the
               prototype can't raise an exception when created, we are safe
               without a try/finally here. */
            var prototype = cheapNew(this);

            /* copy all properties of the includes over if there are any */
            prototype.__mixin_ids = _.clone(prototype.__mixin_ids || {});
            if (properties.__include__)
                for (var i = 0, n = properties.__include__.length; i != n; ++i) {
                    var mixin = properties.__include__[i];
                    if (mixin instanceof nova.Mixin) {
                        _.extend(prototype.__mixin_ids, mixin.__mixin_ids);
                        mixin = mixin.__mixin_properties;
                    }
                    for (var name in mixin) {
                        var value = getOwnProperty(mixin, name);
                        if (value !== undefined)
                            prototype[name] = mixin[name];
                    }
                }

            /* copy class vars from the superclass */
            properties.__classvars__ = properties.__classvars__ || {};
            if (prototype.__classvars__)
                for (var key in prototype.__classvars__)
                    if (!properties.__classvars__[key]) {
                        var value = getOwnProperty(prototype.__classvars__, key);
                        properties.__classvars__[key] = value;
                    }

            /* copy all properties over to the new prototype */
            for (var name in properties) {
                var value = getOwnProperty(properties, name);
                if (name === '__include__' ||
                    value === undefined)
                    continue;

                prototype[name] = typeof value === 'function' && usesSuper(value) ?
                    (function(meth, name) {
                        return function() {
                            var old_super = getOwnProperty(this, '$super');
                            this.$super = super_prototype[name];
                            try {
                                return meth.apply(this, arguments);
                            }
                            finally {
                                setOrUnset(this, '$super', old_super);
                            }
                        };
                    })(value, name) : value
            }

            var class_init = this.__class_init__ || function() {};
            var p_class_init = prototype.__class_init__ || function() {};
            delete prototype.__class_init__;
            var n_class_init = function() {
                class_init.apply(null, arguments);
                p_class_init.apply(null, arguments);
            }
            n_class_init(prototype);

            /* dummy constructor */
            var instance = function() {
                if (disable_constructor)
                    return;
                var proper_this = context === this ? cheapNew(arguments.callee) : this;
                if (proper_this.__init__)
                    proper_this.__init__.apply(proper_this, arguments);
                proper_this.$class = instance;
                return proper_this;
            }

            /* copy all class vars over of any */
            for (var key in properties.__classvars__) {
                var value = getOwnProperty(properties.__classvars__, key);
                if (value !== undefined)
                    instance[key] = value;
            }

            /* copy prototype and constructor over, reattach $extend and
               return the class */
            instance.prototype = prototype;
            instance.constructor = instance;
            instance.$extend = this.$extend;
            instance.$withData = this.$withData;
            instance.__class_init__ = n_class_init;
            return instance;
        };

        /* instanciate with data functionality */
        Class.$withData = function(data) {
            var rv = cheapNew(this);
            for (var key in data) {
                var value = getOwnProperty(data, key);
                if (value !== undefined)
                    rv[key] = value;
            }
            return rv;
        };

        /* export the class */
        this.Class = Class;
    }).call(nova);
    // end of Armin Ronacher's code

    var mixinId = 1;
    nova.Mixin = nova.Class.$extend({
        __init__: function() {
            this.__mixin_properties = {};
            this.__mixin_id = mixinId;
            mixinId++;
            this.__mixin_ids = {};
            this.__mixin_ids[this.__mixin_id] = true;
            _.each(_.toArray(arguments), function(el) {
                if (el instanceof nova.Mixin) {
                    _.extend(this.__mixin_properties, el.__mixin_properties);
                    _.extend(this.__mixin_ids, el.__mixin_ids);
                } else { // object
                    _.extend(this.__mixin_properties, el)
                }
            }, this);
            _.extend(this, this.__mixin_properties);
        }
    });

    nova.Interface = nova.Mixin.$extend({
        __init__: function() {
            var lst = [];
            _.each(_.toArray(arguments), function(el) {
                if (el instanceof nova.Interface) {
                    lst.push(el);
                } else if (el instanceof nova.Mixin) {
                    var tmp = new nova.Interface(el.__mixin_properties);
                    tmp.__mixin_ids = el.__mixin_ids;
                    lst.push(tmp);
                } else { // object
                    var nprops = {};
                    _.each(el, function(v, k) {
                        nprops[k] = function() {
                            throw new nova.NotImplementedError();
                        };
                    });
                    lst.push(nprops);
                }
            });
            this.$super.apply(this, lst);
        }
    });

    nova.hasMixin = function(object, mixin) {
        if (! object)
            return false;
        return (object.__mixin_ids || {})[mixin.__mixin_id] === true;
    };

    var ErrorBase = function() {
    };
    ErrorBase.prototype = new Error();
    ErrorBase.$extend = nova.Class.$extend;
    ErrorBase.$withData = nova.Class.$withData;

    nova.Error = ErrorBase.$extend({
        name: "nova.Error",
        defaultMessage: "",
        __init__: function(message) {
            this.message = message || this.defaultMessage;
        }
    });

    nova.NotImplementedError = nova.Error.$extend({
        name: "nova.NotImplementedError",
        defaultMessage: "This method is not implemented"
    });

    nova.InvalidArgumentError = nova.Error.$extend({
        name: "nova.InvalidArgumentError"
    });

    /**
     * Mixin to express the concept of destroying an object.
     * When an object is destroyed, it should release any resource
     * it could have reserved before.
     */
    nova.Destroyable = new nova.Mixin({
        __init__: function() {
            this.__destroyableDestroyed = false;
        },
        /**
         * Returns true if destroy() was called on the current object.
         */
        isDestroyed : function() {
            return this.__destroyableDestroyed;
        },
        /**
         * Inform the object it should destroy itself, releasing any
         * resource it could have reserved.
         */
        destroy : function() {
            this.__destroyableDestroyed = true;
        }
    });

    /**
     * Mixin to structure objects' life-cycles folowing a parent-children
     * relationship. Each object can a have a parent and multiple children.
     * When an object is destroyed, all its children are destroyed too.
     */
    nova.Parented = new nova.Mixin(nova.Destroyable, {
        __parentedMixin : true,
        __init__: function() {
            nova.Destroyable.__init__.apply(this);
            this.__parentedChildren = [];
            this.__parentedParent = null;
        },
        /**
         * Set the parent of the current object. When calling this method, the
         * parent will also be informed and will return the current object
         * when its getChildren() method is called. If the current object did
         * already have a parent, it is unregistered before, which means the
         * previous parent will not return the current object anymore when its
         * getChildren() method is called.
         */
        setParent : function(parent) {
            if (this.getParent()) {
                if (this.getParent().__parentedMixin) {
                    this.getParent().__parentedChildren = _.without(this
                            .getParent().getChildren(), this);
                }
            }
            this.__parentedParent = parent;
            if (parent && parent.__parentedMixin) {
                parent.__parentedChildren.push(this);
            }
        },
        /**
         * Return the current parent of the object (or null).
         */
        getParent : function() {
            return this.__parentedParent;
        },
        /**
         * Return a list of the children of the current object.
         */
        getChildren : function() {
            return _.clone(this.__parentedChildren);
        },
        destroy : function() {
            _.each(this.getChildren(), function(el) {
                el.destroy();
            });
            this.setParent(undefined);
            nova.Destroyable.destroy.apply(this);
        }
    });

    /*
     * Yes, we steal Backbone's events :)
     * 
     * This class just handle the dispatching of events, it is not meant to be extended,
     * nor used directly. All integration with parenting and automatic unregistration of
     * events is done in the mixin EventDispatcher.
     */
    // (c) 2010-2012 Jeremy Ashkenas, DocumentCloud Inc.
    // Backbone may be freely distributed under the MIT license.
    // For all details and documentation:
    // http://backbonejs.org
    nova.internal.Events = nova.Class.$extend({
        on : function(events, callback, context) {
            var ev;
            events = events.split(/\s+/);
            var calls = this._callbacks || (this._callbacks = {});
            while (ev = events.shift()) {
                var list = calls[ev] || (calls[ev] = {});
                var tail = list.tail || (list.tail = list.next = {});
                tail.callback = callback;
                tail.context = context;
                list.tail = tail.next = {};
            }
            return this;
        },
        off : function(events, callback, context) {
            var ev, calls, node;
            if (!events) {
                delete this._callbacks;
            } else if (calls = this._callbacks) {
                events = events.split(/\s+/);
                while (ev = events.shift()) {
                    node = calls[ev];
                    delete calls[ev];
                    if (!callback || !node)
                        continue;
                    while ((node = node.next) && node.next) {
                        if (node.callback === callback
                                && (!context || node.context === context))
                            continue;
                        this.on(ev, node.callback, node.context);
                    }
                }
            }
            return this;
        },
        callbackList: function() {
            var lst = [];
            _.each(this._callbacks || {}, function(el, eventName) {
                var node = el;
                while ((node = node.next) && node.next) {
                    lst.push([eventName, node.callback, node.context]);
                }
            });
            return lst;
        },
        trigger : function(events) {
            var event, node, calls, tail, args, all, rest;
            if (!(calls = this._callbacks))
                return this;
            all = calls['all'];
            (events = events.split(/\s+/)).push(null);
            // Save references to the current heads & tails.
            while (event = events.shift()) {
                if (all)
                    events.push({
                        next : all.next,
                        tail : all.tail,
                        event : event
                    });
                if (!(node = calls[event]))
                    continue;
                events.push({
                    next : node.next,
                    tail : node.tail
                });
            }
            rest = Array.prototype.slice.call(arguments, 1);
            while (node = events.pop()) {
                tail = node.tail;
                args = node.event ? [ node.event ].concat(rest) : rest;
                while ((node = node.next) !== tail) {
                    node.callback.apply(node.context || this, args);
                }
            }
            return this;
        }
    });
    // end of Backbone's events class
    
    nova.EventDispatcher = new nova.Mixin(nova.Parented, {
        __eventDispatcherMixin: true,
        __init__: function() {
            nova.Parented.__init__.apply(this);
            this.__edispatcherEvents = new nova.internal.Events();
            this.__edispatcherRegisteredEvents = [];
        },
        on: function(events, dest, func) {
            var self = this;
            events = events.split(/\s+/);
            _.each(events, function(eventName) {
                self.__edispatcherEvents.on(eventName, func, dest);
                if (dest && dest.__eventDispatcherMixin) {
                    dest.__edispatcherRegisteredEvents.push({name: eventName, func: func, source: self});
                }
            });
            return this;
        },
        off: function(events, dest, func) {
            var self = this;
            events = events.split(/\s+/);
            _.each(events, function(eventName) {
                self.__edispatcherEvents.off(eventName, func, dest);
                if (dest && dest.__eventDispatcherMixin) {
                    dest.__edispatcherRegisteredEvents = _.filter(dest.__edispatcherRegisteredEvents, function(el) {
                        return !(el.name === eventName && el.func === func && el.source === self);
                    });
                }
            });
            return this;
        },
        trigger: function(events) {
            this.__edispatcherEvents.trigger.apply(this.__edispatcherEvents, arguments);
            return this;
        },
        destroy: function() {
            var self = this;
            _.each(this.__edispatcherRegisteredEvents, function(event) {
                event.source.__edispatcherEvents.off(event.name, event.func, self);
            });
            this.__edispatcherRegisteredEvents = [];
            _.each(this.__edispatcherEvents.callbackList(), function(cal) {
                this.off(cal[0], cal[2], cal[1]);
            }, this);
            this.__edispatcherEvents.off();
            nova.Parented.destroy.apply(this);
        }
    });
    
    nova.Properties = new nova.Mixin(nova.EventDispatcher, {
        __class_init__: function(proto) {
            var props = {};
            _.each(proto.__properties || {}, function(v, k) {
                props[k] = _.clone(v);
            });
            _.each(proto, function(v, k) {
                if (typeof v === "function") {
                    var res = /^((?:get)|(?:set))([A-Z]\w*)$/.exec(k);
                    if (! res)
                        return;
                    var name = res[2][0].toLowerCase() + res[2].slice(1);
                    var prop = props[name] || (props[name] = {});
                    prop[res[1]] = v;
                }
            });
            proto.__properties = props;
        },
        __init__: function() {
            nova.EventDispatcher.__init__.apply(this);
            this.__dynamicProperties = {};
        },
        set: function(arg1, arg2) {
            var self = this;
            var map;
            if (typeof arg1 === "string") {
                map = {};
                map[arg1] = arg2;
            } else {
                map = arg1;
            }
            var tmp_set = this.__props_setting;
            this.__props_setting = false;
            _.each(map, function(val, key) {
                var prop = self.__properties[key];
                if (prop) {
                    if (! prop.set)
                        throw new nova.InvalidArgumentError("Property " + key + " does not have a setter method.");
                    prop.set.call(self, val);
                } else {
                    self.fallbackSet(key, val);
                }
            });
            this.__props_setting = tmp_set;
            if (! this.__props_setting && this.__props_setted) {
                this.__props_setted = false;
                self.trigger("change", self);
            }
        },
        get: function(key) {
            var prop = this.__properties[key];
            if (prop) {
                if (! prop.get)
                    throw new nova.InvalidArgumentError("Property " + key + " does not have a getter method.");
                return prop.get.call(this);
            } else {
                return this.fallbackGet(key);
            }
        },
        fallbackSet: function(key, val) {
            throw new nova.InvalidArgumentError("Property " + key + " is not defined.");
        },
        fallbackGet: function(key) {
            throw new nova.InvalidArgumentError("Property " + key + " is not defined.");
        },
        trigger: function(name) {
            nova.EventDispatcher.trigger.apply(this, arguments);
            if (/(\s|^)change\:.*/.exec(name)) {
                if (! this.__props_setting)
                    this.trigger("change");
                else
                    this.__props_setted = true;
            }
        }
    });

    nova.DynamicProperties = new nova.Mixin(nova.Properties, {
        __init__: function() {
            nova.Properties.__init__.apply(this);
            this.__dynamicProperties = {};
        },
        fallbackSet: function(key, val) {
            var tmp = this.__dynamicProperties[key];
            if (tmp === val)
                return;
            this.__dynamicProperties[key] = val;
            this.trigger("change:" + key, this, {
                oldValue: tmp,
                newValue: val
            });
        },
        fallbackGet: function(key) {
            return this.__dynamicProperties[key];
        }
    });
    
    nova.Widget = nova.Class.$extend({
        __include__ : [nova.DynamicProperties],
        tagName: 'div',
        className: '',
        attributes: {},
        events: {},
        __init__: function(parent) {
            nova.Properties.__init__.apply(this);
            this.__widget_element = $(document.createElement(this.tagName));
            this.$().addClass(this.className);
            _.each(this.attributes, function(val, key) {
                this.$().attr(key, val);
            }, this);
            _.each(this.events, function(val, key) {
                key = key.split(" ");
                val = _.bind(typeof val === "string" ? this[val] : val, this);
                if (key.length > 1) {
                    this.$().on(key[0], key[1], val);
                } else {
                    this.$().on(key[0], val);
                }
            }, this);
    
            this.setParent(parent);
        },
        $: function(attr) {
            if (attr)
                return this.__widget_element.find.apply(this.__widget_element, arguments);
            else
                return this.__widget_element;
        },
        /**
         * Destroys the current widget, also destroys all its children before destroying itself.
         */
        destroy: function() {
            _.each(this.getChildren(), function(el) {
                el.destroy();
            });
            this.$().remove();
            nova.Properties.destroy.apply(this);
        },
        /**
         * Renders the current widget and appends it to the given jQuery object or Widget.
         *
         * @param target A jQuery object or a Widget instance.
         */
        appendTo: function(target) {
            this.$().appendTo(target);
            return this.render();
        },
        /**
         * Renders the current widget and prepends it to the given jQuery object or Widget.
         *
         * @param target A jQuery object or a Widget instance.
         */
        prependTo: function(target) {
            this.$().prependTo(target);
            return this.render();
        },
        /**
         * Renders the current widget and inserts it after to the given jQuery object or Widget.
         *
         * @param target A jQuery object or a Widget instance.
         */
        insertAfter: function(target) {
            this.$().insertAfter(target);
            return this.render();
        },
        /**
         * Renders the current widget and inserts it before to the given jQuery object or Widget.
         *
         * @param target A jQuery object or a Widget instance.
         */
        insertBefore: function(target) {
            this.$().insertBefore(target);
            return this.render();
        },
        /**
         * Renders the current widget and replaces the given jQuery object.
         *
         * @param target A jQuery object or a Widget instance.
         */
        replace: function(target) {
            this.$().replace(target);
            return this.render();
        },
        /**
         * This is the method to implement to render the Widget.
         */
        render: function() {}
    });

    /*
        Nova Template Engine
    */
    var escape_ = function(text) {
        return JSON.stringify(text);
    }
    var indent_ = function(txt) {
        var tmp = _.map(txt.split("\n"), function(x) { return "    " + x; });
        tmp.pop();
        tmp.push("");
        return tmp.join("\n");
    };
    var tparams = {
        def_begin: /<%\s*def\s+(?:name=(?:(?:"(.+?)")|(?:'(.+?)')))\s*>/g,
        def_end: /<\/%\s*def\s*>/g,
        comment_multi_begin: /<%\s*doc\s*>/g,
        comment_multi_end: /<\/%\s*doc\s*>/g,
        eval_long_begin: /<%/g,
        eval_long_end: /%>/g,
        eval_short_begin: /(?:^|\n)[[ \t]*%(?!{)/g,
        eval_short_end: /\n|$/g,
        escape_begin: /\${/g,
        interpolate_begin: /%{/g,
        comment_begin: /##/g,
        comment_end: /\n|$/g
    };
    // /<%\s*def\s+(?:name=(?:"(.+?)"))\s*%>([\s\S]*?)<%\s*def\s*%>/g
    var allbegin = new RegExp(
        "((?:\\\\)*)(" +
        "(" + tparams.def_begin.source + ")|" +
        "(" + tparams.def_end.source + ")|" +
        "(" + tparams.comment_multi_begin.source + ")|" +
        "(" + tparams.eval_long_begin.source + ")|" +
        "(" + tparams.interpolate_begin.source + ")|" +
        "(" + tparams.eval_short_begin.source + ")|" +
        "(" + tparams.escape_begin.source + ")|" +
        "(" + tparams.comment_begin.source + ")" +
        ")"
    , "g");
    allbegin.global = true;
    var regexes = {
        slashes: 1,
        match: 2,
        def_begin: 3,
        def_name1: 4,
        def_name2: 5,
        def_end: 6,
        comment_multi_begin: 7,
        eval_long: 8,
        interpolate: 9,
        eval_short: 10,
        escape: 11,
        comment: 12
    };
    var regex_count = 4;

    var compileTemplate = function(text, options) {
        options = _.extend({start: 0, indent: true}, options);
        start = options.start;
        var source = "";
        var current = start;
        allbegin.lastIndex = current;
        var text_end = text.length;
        var restart = end;
        var found;
        var functions = [];
        var indent = options.indent ? indent_ : function (txt) { return txt; };
        var rmWhite = options.removeWhitespaces ? function(txt) {
            if (! txt)
                return txt;
            txt = _.map(txt.split("\n"), function(x) { return x.trim() });
            var last = txt.pop();
            txt = _.reject(txt, function(x) { return !x });
            txt.push(last);
            return txt.join("\n") || "\n";
        } : function(x) { return x };
        while (found = allbegin.exec(text)) {
            var to_add = rmWhite(text.slice(current, found.index));
            source += to_add ? "__p+=" + escape_(to_add) + ";\n" : '';
            current = found.index;

            // slash escaping handling
            var slashes = found[regexes.slashes] || "";
            var nbr = slashes.length;
            var nslash = slashes.slice(0, Math.floor(nbr / 2));
            source += nbr !== 0 ? "__p+=" + escape_(nslash) + ";\n" : "";
            if (nbr % 2 !== 0) {
                source += "__p+=" + escape_(found[regexes.match]) + ";\n";
                current = found.index + found[0].length;
                allbegin.lastIndex = current;
                continue;
            }

            if (found[regexes.def_begin]) {
                var sub_compile = compileTemplate(text, _.extend({}, options, {start: found.index + found[0].length}));
                var name = (found[regexes.def_name1] || found[regexes.def_name2]);
                source += "var " + name  + " = function(context) {\n" + indent(sub_compile.header + sub_compile.source
                    + sub_compile.footer) + "}\n";
                functions.push(name);
                current = sub_compile.end;
            } else if (found[regexes.def_end]) {
                text_end = found.index;
                restart = found.index + found[0].length;
                break;
            } else if (found[regexes.comment_multi_begin]) {
                tparams.comment_multi_end.lastIndex = found.index + found[0].length;
                var end = tparams.comment_multi_end.exec(text);
                if (!end)
                    throw new Error("<%doc> without corresponding </%doc>");
                current = end.index + end[0].length;
            } else if (found[regexes.eval_long]) {
                tparams.eval_long_end.lastIndex = found.index + found[0].length;
                var end = tparams.eval_long_end.exec(text);
                if (!end)
                    throw new Error("<% without matching %>");
                var code = text.slice(found.index + found[0].length, end.index);
                code = _(code.split("\n")).chain().map(function(x) { return x.trim() })
                    .reject(function(x) { return !x }).value().join("\n");
                source += code + "\n";
                current = end.index + end[0].length;
            } else if (found[regexes.interpolate]) {
                var braces = /{|}/g;
                braces.lastIndex = found.index + found[0].length;
                var b_count = 1;
                var brace;
                while (brace = braces.exec(text)) {
                    if (brace[0] === "{")
                        b_count++;
                    else {
                        b_count--;
                    }
                    if (b_count === 0)
                        break;
                }
                if (b_count !== 0)
                    throw new Error("%{ without a matching }");
                source += "__p+=" + text.slice(found.index + found[0].length, brace.index) + ";\n"
                current = brace.index + brace[0].length;
            } else if (found[regexes.eval_short]) {
                tparams.eval_short_end.lastIndex = found.index + found[0].length;
                var end = tparams.eval_short_end.exec(text);
                if (!end)
                    throw new Error("impossible state!!");
                source += text.slice(found.index + found[0].length, end.index).trim() + "\n";
                current = end.index;
            } else if (found[regexes.escape]) {
                var braces = /{|}/g;
                braces.lastIndex = found.index + found[0].length;
                var b_count = 1;
                var brace;
                while (brace = braces.exec(text)) {
                    if (brace[0] === "{")
                        b_count++;
                    else {
                        b_count--;
                    }
                    if (b_count === 0)
                        break;
                }
                if (b_count !== 0)
                    throw new Error("${ without a matching }");
                source += "__p+=_.escape(" + text.slice(found.index + found[0].length, brace.index) + ");\n"
                current = brace.index + brace[0].length;
            } else { // comment 
                tparams.comment_end.lastIndex = found.index + found[0].length;
                var end = tparams.comment_end.exec(text);
                if (!end)
                    throw new Error("impossible state!!");
                current = end.index + end[0].length;
            }
            allbegin.lastIndex = current;
        }
        var to_add = rmWhite(text.slice(current, text_end));
        source += to_add ? "__p+=" + escape_(to_add) + ";\n" : "";

        var header = "var __p = ''; var print = function() { __p+=Array.prototype.join.call(arguments, '') };\n" +
          "with (context || {}) {\n";
        var footer = "}\nreturn __p;\n";
        source = indent(source);

        return {
            header: header,
            source: source,
            footer: footer,
            end: restart,
            functions: functions,
        };
    };

    nova.TemplateEngine = nova.Class.$extend({
        __init__: function() {
            this.resetEnvironment();
            this.options = {
                includeInDom: $ ? true : false,
                indent: true,
                removeWhitespaces: true,
            };
        },
        loadFile: function(filename) {
            var self = this;
            return $.get(filename).pipe(function(content) {
                return self.loadFileContent(content);
            });
        },
        loadFileContent: function(file_content) {
            var code = this.compileFile(file_content);

            if (this.options.includeInDom) {
                var varname = _.uniqueId("novajstemplate");
                var previous = window[varname];
                code = "window." + varname + " = " + code + ";";
                var def = $.Deferred();
                var script   = document.createElement("script");
                script.type  = "text/javascript";
                script.text  = code;
                $("head")[0].appendChild(script);
                $(script).ready(function() {
                    def.resolve();
                });
                def.then(_.bind(function() {
                    var tmp = window[varname];
                    window[varname] = previous;
                    this.includeTemplates(tmp);
                }, this));
                return def;
            } else {
                console.log("return (" + code + ")(context);");
                return this.includeTemplates(new Function('context', "return (" + code + ")(context);"));
            }
        },
        compileFile: function(file_content) {
            var result = compileTemplate(file_content, _.extend({}, this.options));
            var to_append = "";
            _.each(result.functions, function(name) {
                to_append += name + ": " + name + ",\n";
            }, this);
            to_append = this.options.indent ? indent_(to_append) : to_append;
            to_append = "return {\n" + to_append + "};\n";
            to_append = this.options.indent ? indent_(to_append) : to_append;
            var code = "function(context) {\n" + result.header +
                result.source + to_append + result.footer + "}\n";
            return code;
        },
        includeTemplates: function(fct) {
            var add = _.extend({engine: this}, this._env);
            var functions = fct(add);
            _.each(functions, function(func, name) {
                if (this[name])
                    throw new Error("The template '" + name + "' is already defined");
                this[name] = func;
            }, this);
        },
        buildTemplate: function(text) {
            var comp = compileTemplate(text, _.extend({}, this.options));
            var result = comp.header + comp.source + comp.footer;
            var add = _.extend({engine: this}, this._env);
            var func = new Function('context', result);
            return function(data) {
                return func.call(this, _.extend(add, data));
            };
        },
        eval: function(text, context) {
            return this.buildTemplate(text)(context);
        },
        resetEnvironment: function(nenv) {
            this._env = {_: _};
            this.extendEnvironment(nenv);
        },
        extendEnvironment: function(env) {
            _.extend(this._env, env || {});
        },
    });

    return nova;
};
})();
