
(function() {

if (typeof(console) === "undefined") {
    // Even IE9 only exposes console object if debug window opened
    window.console = {};
    ('log error debug info warn assert clear dir dirxml trace group'
        + ' groupCollapsed groupEnd time timeEnd profile profileEnd count'
        + ' exception').split(/\s+/).forEach(function(property) {
            console[property] = _.identity;
    });
}

var instance = openerp;
openerp.web.core = {};

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

/*
    Some retro-compatibility.
*/
instance.web.JsonRPC = instance.web.Session;

/** Session openerp specific RPC class */
instance.web.Session.include( /** @lends instance.web.Session# */{
    init: function() {
        this._super.apply(this, arguments);
        this.debug = ($.deparam($.param.querystring()).debug !== undefined);
        // TODO: session store in cookie should be optional
        this.name = instance._session_id;
        this.qweb_mutex = new $.Mutex();
    },
    /**
     * Setup a sessionm
     */
    session_bind: function(origin) {
        var self = this;
        this.setup(origin);
        instance.web.qweb.default_dict['_s'] = this.origin;
        this.uid = null;
        this.username = null;
        this.user_context= {};
        this.db = null;
        this.module_list = instance._modules.slice();
        this.module_loaded = {};
        _(this.module_list).each(function (mod) {
            self.module_loaded[mod] = true;
        });
        this.active_id = null;
        return this.session_init();
    },
    /**
     * Init a session, reloads from cookie, if it exists
     */
    session_init: function () {
        var self = this;
        return this.session_reload().then(function(result) {
            var modules = instance._modules.join(',');
            var deferred = self.load_qweb(modules);
            if(self.session_is_valid()) {
                return deferred.then(function() { return self.load_modules(); });
            }
            return $.when(
                    deferred,
                    self.rpc('/web/webclient/bootstrap_translations', {mods: instance._modules}).then(function(trans) {
                        instance.web._t.database.set_bundle(trans);
                    })
            );
        });
    },
    session_is_valid: function() {
        var db = $.deparam.querystring().db;
        if (db && this.db !== db) {
            return false;
        }
        return !!this.uid;
    },
    /**
     * The session is validated by restoration of a previous session
     */
    session_authenticate: function() {
        var self = this;
        return $.when(this._super.apply(this, arguments)).then(function() {
            return self.load_modules();
        });
    },
    session_logout: function() {
        $.bbq.removeState();
        return this.rpc("/web/session/destroy", {});
    },
    get_cookie: function (name) {
        if (!this.name) { return null; }
        var nameEQ = this.name + '|' + name + '=';
        var cookies = document.cookie.split(';');
        for(var i=0; i<cookies.length; ++i) {
            var cookie = cookies[i].replace(/^\s*/, '');
            if(cookie.indexOf(nameEQ) === 0) {
                try {
                    return JSON.parse(decodeURIComponent(cookie.substring(nameEQ.length)));
                } catch(err) {
                    // wrong cookie, delete it
                    this.set_cookie(name, '', -1);
                }
            }
        }
        return null;
    },
    /**
     * Create a new cookie with the provided name and value
     *
     * @private
     * @param name the cookie's name
     * @param value the cookie's value
     * @param ttl the cookie's time to live, 1 year by default, set to -1 to delete
     */
    set_cookie: function (name, value, ttl) {
        if (!this.name) { return; }
        ttl = ttl || 24*60*60*365;
        document.cookie = [
            this.name + '|' + name + '=' + encodeURIComponent(JSON.stringify(value)),
            'path=/',
            'max-age=' + ttl,
            'expires=' + new Date(new Date().getTime() + ttl*1000).toGMTString()
        ].join(';');
    },
    /**
     * Load additional web addons of that instance and init them
     *
     */
    load_modules: function() {
        var self = this;
        return this.rpc('/web/session/modules', {}).then(function(result) {
            var all_modules = _.uniq(self.module_list.concat(result));
            var to_load = _.difference(result, self.module_list).join(',');
            self.module_list = all_modules;

            var loaded = self.load_translations();
            var locale = "/web/webclient/locale/" + self.user_context.lang || 'en_US';
            var file_list = [ locale ];
            if(to_load.length) {
                loaded = $.when(
                    loaded,
                    self.rpc('/web/webclient/csslist', {mods: to_load}).done(self.load_css.bind(self)),
                    self.load_qweb(to_load),
                    self.rpc('/web/webclient/jslist', {mods: to_load}).done(function(files) {
                        file_list = file_list.concat(files);
                    })
                );
            }
            return loaded.then(function () {
                return self.load_js(file_list);
            }).done(function() {
                self.on_modules_loaded();
                self.trigger('module_loaded');
            });
        });
    },
    load_translations: function() {
        return instance.web._t.database.load_translations(this, this.module_list, this.user_context.lang);
    },
    load_css: function (files) {
        var self = this;
        _.each(files, function (file) {
            openerp.loadCSS(self.url(file, null));
        });
    },
    load_js: function(files) {
        var self = this;
        var d = $.Deferred();
        if (files.length !== 0) {
            var file = files.shift();
            var url = self.url(file, null);
            openerp.loadJS(url).done(d.resolve);
        } else {
            d.resolve();
        }
        return d;
    },
    load_qweb: function(mods) {
        var self = this;
        self.qweb_mutex.exec(function() {
            return self.rpc('/web/proxy/load', {path: '/web/webclient/qweb?mods=' + mods}).then(function(xml) {
                if (!xml) { return; }
                instance.web.qweb.add_template(_.str.trim(xml));
            });
        });
        return self.qweb_mutex.def;
    },
    on_modules_loaded: function() {
        for(var j=0; j<this.module_list.length; j++) {
            var mod = this.module_list[j];
            if(this.module_loaded[mod])
                continue;
            instance[mod] = {};
            // init module mod
            var fct = instance._openerp[mod];
            if(typeof(fct) === "function") {
                instance._openerp[mod] = {};
                for (var k in fct) {
                    instance._openerp[mod][k] = fct[k];
                }
                fct(instance, instance._openerp[mod]);
            }
            this.module_loaded[mod] = true;
        }
    },
    /**
     * Cooperative file download implementation, for ajaxy APIs.
     *
     * Requires that the server side implements an httprequest correctly
     * setting the `fileToken` cookie to the value provided as the `token`
     * parameter. The cookie *must* be set on the `/` path and *must not* be
     * `httpOnly`.
     *
     * It would probably also be a good idea for the response to use a
     * `Content-Disposition: attachment` header, especially if the MIME is a
     * "known" type (e.g. text/plain, or for some browsers application/json
     *
     * @param {Object} options
     * @param {String} [options.url] used to dynamically create a form
     * @param {Object} [options.data] data to add to the form submission. If can be used without a form, in which case a form is created from scratch. Otherwise, added to form data
     * @param {HTMLFormElement} [options.form] the form to submit in order to fetch the file
     * @param {Function} [options.success] callback in case of download success
     * @param {Function} [options.error] callback in case of request error, provided with the error body
     * @param {Function} [options.complete] called after both ``success`` and ``error` callbacks have executed
     */
    get_file: function (options) {
        // need to detect when the file is done downloading (not used
        // yet, but we'll need it to fix the UI e.g. with a throbber
        // while dump is being generated), iframe load event only fires
        // when the iframe content loads, so we need to go smarter:
        // http://geekswithblogs.net/GruffCode/archive/2010/10/28/detecting-the-file-download-dialog-in-the-browser.aspx
        var timer, token = new Date().getTime(),
            cookie_name = 'fileToken', cookie_length = cookie_name.length,
            CHECK_INTERVAL = 1000, id = _.uniqueId('get_file_frame'),
            remove_form = false;


        // iOS devices doesn't allow iframe use the way we do it,
        // opening a new window seems the best way to workaround
        if (navigator.userAgent.match(/(iPod|iPhone|iPad)/)) {
            var params = _.extend({}, options.data || {}, {token: token});
            var url = this.url(options.url, params);
            instance.web.unblockUI();
            return window.open(url);
        }

        var $form, $form_data = $('<div>');

        var complete = function () {
            if (options.complete) { options.complete(); }
            clearTimeout(timer);
            $form_data.remove();
            $target.remove();
            if (remove_form && $form) { $form.remove(); }
        };
        var $target = $('<iframe style="display: none;">')
            .attr({id: id, name: id})
            .appendTo(document.body)
            .load(function () {
                try {
                    if (options.error) {
                        var body = this.contentDocument.body;
                        var node = body.childNodes[1] || body.childNodes[0];
                        options.error(JSON.parse(node.textContent));
                    }
                } finally {
                    complete();
                }
            });

        if (options.form) {
            $form = $(options.form);
        } else {
            remove_form = true;
            $form = $('<form>', {
                action: options.url,
                method: 'POST'
            }).appendTo(document.body);
        }

        var hparams = _.extend({}, options.data || {}, {token: token});
        if (this.override_session)
            hparams.session_id = this.session_id;
        _.each(hparams, function (value, key) {
                var $input = $form.find('[name=' + key +']');
                if (!$input.length) {
                    $input = $('<input type="hidden" name="' + key + '">')
                        .appendTo($form_data);
                }
                $input.val(value);
            });

        $form
            .append($form_data)
            .attr('target', id)
            .get(0).submit();

        var waitLoop = function () {
            var cookies = document.cookie.split(';');
            // setup next check
            timer = setTimeout(waitLoop, CHECK_INTERVAL);
            for (var i=0; i<cookies.length; ++i) {
                var cookie = cookies[i].replace(/^\s*/, '');
                if (!cookie.indexOf(cookie_name === 0)) { continue; }
                var cookie_val = cookie.substring(cookie_length + 1);
                if (parseInt(cookie_val, 10) !== token) { continue; }

                // clear cookie
                document.cookie = _.str.sprintf("%s=;expires=%s;path=/",
                    cookie_name, new Date().toGMTString());
                if (options.success) { options.success(); }
                complete();
                return;
            }
        };
        timer = setTimeout(waitLoop, CHECK_INTERVAL);
    },
    synchronized_mode: function(to_execute) {
        var synch = this.synch;
        this.synch = true;
        try {
            return to_execute();
        } finally {
            this.synch = synch;
        }
    }
});


/**
 * Event Bus used to bind events scoped in the current instance
 */
instance.web.Bus = instance.web.Class.extend(instance.web.EventDispatcherMixin, {
    init: function() {
        instance.web.EventDispatcherMixin.init.call(this, parent);
        var self = this;
        // TODO fme: allow user to bind keys for some global actions.
        //           check gtk bindings
        // http://unixpapa.com/js/key.html
        _.each('click,dblclick,keydown,keypress,keyup'.split(','), function(evtype) {
            $('html').on(evtype, function(ev) {
                self.trigger(evtype, ev);
            });
        });
        _.each('resize,scroll'.split(','), function(evtype) {
            $(window).on(evtype, function(ev) {
                self.trigger(evtype, ev);
            });
        });
    }
});
instance.web.bus = new instance.web.Bus();

instance.web.TranslationDataBase.include({
    set_bundle: function(translation_bundle) {
        this._super(translation_bundle);
        if (translation_bundle.lang_parameters) {
            this.parameters.grouping = py.eval(this.parameters.grouping);
        }
    },
});

/** Custom jQuery plugins */
$.browser = $.browser || {};
if(navigator.appVersion.indexOf("MSIE") !== -1) {
    $.browser.msie = 1;
}
$.fn.getAttributes = function() {
    var o = {};
    if (this.length) {
        for (var attr, i = 0, attrs = this[0].attributes, l = attrs.length; i < l; i++) {
            attr = attrs.item(i);
            o[attr.nodeName] = attr.value;
        }
    }
    return o;
};
$.fn.openerpClass = function(additionalClass) {
    // This plugin should be applied on top level elements
    additionalClass = additionalClass || '';
    if (!!$.browser.msie) {
        additionalClass += ' openerp_ie';
    }
    return this.each(function() {
        $(this).addClass('openerp ' + additionalClass);
    });
};
$.fn.openerpBounce = function() {
    return this.each(function() {
        $(this).css('box-sizing', 'content-box').effect('bounce', {distance: 18, times: 5}, 250);
    });
};

/** Jquery extentions */
$.Mutex = openerp.Mutex;

$.async_when = function() {
    var async = false;
    var def = $.Deferred();
    $.when.apply($, arguments).done(function() {
        var args = arguments;
        var action = function() {
            def.resolve.apply(def, args);
        };
        if (async)
            action();
        else
            setTimeout(action, 0);
    }).fail(function() {
        var args = arguments;
        var action = function() {
            def.reject.apply(def, args);
        };
        if (async)
            action();
        else
            setTimeout(action, 0);
    });
    async = true;
    return def;
};

// special tweak for the web client
var old_async_when = $.async_when;
$.async_when = function() {
    if (instance.session.synch)
        return $.when.apply(this, arguments);
    else
        return old_async_when.apply(this, arguments);
};

/** Setup default session */
instance.session = new instance.web.Session();

/**
 * Lazy translation function, only performs the translation when actually
 * printed (e.g. inserted into a template)
 *
 * Useful when defining translatable strings in code evaluated before the
 * translation database is loaded, as class attributes or at the top-level of
 * an OpenERP Web module
 *
 * @param {String} s string to translate
 * @returns {Object} lazy translation object
 */
instance.web._lt = function (s) {
    return {toString: function () { return instance.web._t(s); }};
};
instance.web.qweb.debug = instance.session.debug;
_.extend(instance.web.qweb.default_dict, {
    '__debug__': instance.session.debug,
    'moment': function(date) { return new moment(date); },
});
instance.web.qweb.preprocess_node = function() {
    // Note that 'this' is the Qweb Node
    switch (this.node.nodeType) {
        case Node.TEXT_NODE:
        case Node.CDATA_SECTION_NODE:
            // Text and CDATAs
            var translation = this.node.parentNode.attributes['t-translation'];
            if (translation && translation.value === 'off') {
                return;
            }
            var match = /^(\s*)([\s\S]+?)(\s*)$/.exec(this.node.data);
            if (match) {
                this.node.data = match[1] + instance.web._t(match[2]) + match[3];
            }
            break;
        case Node.ELEMENT_NODE:
            // Element
            var attr, attrs = ['label', 'title', 'alt', 'placeholder'];
            while ((attr = attrs.pop())) {
                if (this.attributes[attr]) {
                    this.attributes[attr] = instance.web._t(this.attributes[attr]);
                }
            }
    }
};

/** Setup jQuery timeago */
var _t = instance.web._t;
/*
 * Strings in timeago are "composed" with prefixes, words and suffixes. This
 * makes their detection by our translating system impossible. Use all literal
 * strings we're using with a translation mark here so the extractor can do its
 * job.
 */
{
    _t('less than a minute ago');
    _t('about a minute ago');
    _t('%d minutes ago');
    _t('about an hour ago');
    _t('%d hours ago');
    _t('a day ago');
    _t('%d days ago');
    _t('about a month ago');
    _t('%d months ago');
    _t('about a year ago');
    _t('%d years ago');
}

instance.session.on('module_loaded', this, function () {
    // provide timeago.js with our own translator method
    $.timeago.settings.translator = instance.web._t;
});

/** Setup blockui */
if ($.blockUI) {
    $.blockUI.defaults.baseZ = 1100;
    $.blockUI.defaults.message = '<div class="openerp oe_blockui_spin_container" style="background-color: transparent;">';
    $.blockUI.defaults.css.border = '0';
    $.blockUI.defaults.css["background-color"] = '';
}

var messages_by_seconds = function() {
    return [
        [0, _t("Loading...")],
        [20, _t("Still loading...")],
        [60, _t("Still loading...<br />Please be patient.")],
        [120, _t("Don't leave yet,<br />it's still loading...")],
        [300, _t("You may not believe it,<br />but the application is actually loading...")],
        [420, _t("Take a minute to get a coffee,<br />because it's loading...")],
        [3600, _t("Maybe you should consider reloading the application by pressing F5...")]
    ];
};

instance.web.Throbber = instance.web.Widget.extend({
    template: "Throbber",
    start: function() {
        var opts = {
          lines: 13, // The number of lines to draw
          length: 7, // The length of each line
          width: 4, // The line thickness
          radius: 10, // The radius of the inner circle
          rotate: 0, // The rotation offset
          color: '#FFF', // #rgb or #rrggbb
          speed: 1, // Rounds per second
          trail: 60, // Afterglow percentage
          shadow: false, // Whether to render a shadow
          hwaccel: false, // Whether to use hardware acceleration
          className: 'spinner', // The CSS class to assign to the spinner
          zIndex: 2e9, // The z-index (defaults to 2000000000)
          top: 'auto', // Top position relative to parent in px
          left: 'auto' // Left position relative to parent in px
        };
        this.spin = new Spinner(opts).spin(this.$el[0]);
        this.start_time = new Date().getTime();
        this.act_message();
    },
    act_message: function() {
        var self = this;
        setTimeout(function() {
            if (self.isDestroyed())
                return;
            var seconds = (new Date().getTime() - self.start_time) / 1000;
            var mes;
            _.each(messages_by_seconds(), function(el) {
                if (seconds >= el[0])
                    mes = el[1];
            });
            self.$(".oe_throbber_message").html(mes);
            self.act_message();
        }, 1000);
    },
    destroy: function() {
        if (this.spin)
            this.spin.stop();
        this._super();
    },
});
instance.web.Throbber.throbbers = [];

instance.web.blockUI = function() {
    var tmp = $.blockUI.apply($, arguments);
    var throbber = new instance.web.Throbber();
    instance.web.Throbber.throbbers.push(throbber);
    throbber.appendTo($(".oe_blockui_spin_container"));
    return tmp;
};
instance.web.unblockUI = function() {
    _.each(instance.web.Throbber.throbbers, function(el) {
        el.destroy();
    });
    return $.unblockUI.apply($, arguments);
};


/* Bootstrap defaults overwrite */
$.fn.tooltip.Constructor.DEFAULTS.placement = 'auto top';
$.fn.tooltip.Constructor.DEFAULTS.html = true;
$.fn.tooltip.Constructor.DEFAULTS.trigger = 'hover focus click';
$.fn.tooltip.Constructor.DEFAULTS.container = 'body';
//overwrite bootstrap tooltip method to prevent showing 2 tooltip at the same time
var bootstrap_show_function = $.fn.tooltip.Constructor.prototype.show;
$.fn.modal.Constructor.prototype.enforceFocus = function () { };
$.fn.tooltip.Constructor.prototype.show = function () {
    $('.tooltip').remove();
    //the following fix the bug when using placement
    //auto and the parent element does not exist anymore resulting in
    //an error. This should be remove once we updade bootstrap to a version that fix the bug
    //edit: bug has been fixed here : https://github.com/twbs/bootstrap/pull/13752
    var e = $.Event('show.bs.' + this.type);
    var inDom = $.contains(document.documentElement, this.$element[0]);
    if (e.isDefaultPrevented() || !inDom) return;
    return bootstrap_show_function.call(this);
};

/**
 * Registry for all the client actions key: tag value: widget
 */
instance.web.client_actions = new instance.web.Registry();

})();

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
