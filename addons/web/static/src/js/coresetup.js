/*---------------------------------------------------------
 * OpenERP Web core
 *--------------------------------------------------------*/
var console;
if (!console) {
    console = {log: function () {}};
}
if (!console.debug) {
    console.debug = console.log;
}

openerp.web.coresetup = function(instance) {

/**
 * @deprecated use :class:`instance.web.Widget`
 */
instance.web.OldWidget = instance.web.Widget.extend({
    init: function(parent, element_id) {
        this._super(parent);
        this.element_id = element_id;
        this.element_id = this.element_id || _.uniqueId('widget-');
        var tmp = document.getElementById(this.element_id);
        this.$element = tmp ? $(tmp) : $(document.createElement(this.tagName));
    },
    renderElement: function() {
        var rendered = this.render();
        if (rendered) {
            var elem = $(rendered);
            this.$element.replaceWith(elem);
            this.$element = elem;
        }
        return this;
    },
    render: function (additional) {
        if (this.template)
            return instance.web.qweb.render(this.template, _.extend({widget: this}, additional || {}));
        return null;
    }
});

/** Session openerp specific RPC class */
instance.web.Session = instance.web.JsonRPC.extend( /** @lends instance.web.Session# */{
    init: function() {
        this._super.apply(this, arguments);
        // TODO: session store in cookie should be optional
        this.name = instance._session_id;
        this.qweb_mutex = new $.Mutex();
    },
    rpc: function(url, params, success_callback, error_callback) {
        params.session_id = this.session_id;
        return this._super(url, params, success_callback, error_callback);
    },
    /**
     * Setup a sessionm
     */
    session_bind: function(origin) {
        var self = this;
        this.setup(origin);
        instance.web.qweb.default_dict['_s'] = this.origin;
        this.session_id = false;
        this.uid = false;
        this.username = false;
        this.user_context= {};
        this.db = false;
        this.openerp_entreprise = false;
        this.module_list = instance._modules.slice();
        this.module_loaded = {};
        _(this.module_list).each(function (mod) {
            self.module_loaded[mod] = true;
        });
        this.context = {};
        this.active_id = null;
        return this.session_init();
    },
    /**
     * Init a session, reloads from cookie, if it exists
     */
    session_init: function () {
        var self = this;
        // TODO: session store in cookie should be optional
        this.session_id = this.get_cookie('session_id');
        return this.session_reload().pipe(function(result) {
            var modules = instance._modules.join(',');
            var deferred = self.rpc('/web/webclient/qweblist', {mods: modules}).pipe(self.do_load_qweb);
            if(self.session_is_valid()) {
                return deferred.pipe(function() { return self.load_modules(); });
            }
            return deferred;
        });
    },
    /**
     * (re)loads the content of a session: db name, username, user id, session
     * context and status of the support contract
     *
     * @returns {$.Deferred} deferred indicating the session is done reloading
     */
    session_reload: function () {
        var self = this;
        return this.rpc("/web/session/get_session_info", {}).then(function(result) {
            // If immediately follows a login (triggered by trying to restore
            // an invalid session or no session at all), refresh session data
            // (should not change, but just in case...)
            _.extend(self, {
                session_id: result.session_id,
                db: result.db,
                username: result.login,
                uid: result.uid,
                user_context: result.context,
                openerp_entreprise: result.openerp_entreprise
            });
        });
    },
    session_is_valid: function() {
        return !!this.uid;
    },
    /**
     * The session is validated either by login or by restoration of a previous session
     */
    session_authenticate: function(db, login, password, _volatile) {
        var self = this;
        var base_location = document.location.protocol + '//' + document.location.host;
        var params = { db: db, login: login, password: password, base_location: base_location };
        return this.rpc("/web/session/authenticate", params).pipe(function(result) {
            if (!result.uid) {
                return $.Deferred().reject();
            }

            _.extend(self, {
                session_id: result.session_id,
                db: result.db,
                username: result.login,
                uid: result.uid,
                user_context: result.context,
                openerp_entreprise: result.openerp_entreprise
            });
            if (!_volatile) {
                self.set_cookie('session_id', self.session_id);
            }
            return self.load_modules();
        });
    },
    session_logout: function() {
        this.set_cookie('session_id', '');
        return this.rpc("/web/session/destroy", {});
    },
    on_session_valid: function() {
    },
    /**
     * Called when a rpc call fail due to an invalid session.
     * By default, it's a noop
     */
    on_session_invalid: function(retry_callback) {
    },
    /**
     * Fetches a cookie stored by an openerp session
     *
     * @private
     * @param name the cookie's name
     */
    get_cookie: function (name) {
        if (!this.name) { return null; }
        var nameEQ = this.name + '|' + name + '=';
        var cookies = document.cookie.split(';');
        for(var i=0; i<cookies.length; ++i) {
            var cookie = cookies[i].replace(/^\s*/, '');
            if(cookie.indexOf(nameEQ) === 0) {
                return JSON.parse(decodeURIComponent(cookie.substring(nameEQ.length)));
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
     * @param {Boolean} [no_session_valid_signal=false] prevents load_module from triggering ``on_session_valid``.
     */
    load_modules: function(no_session_valid_signal) {
        var self = this;
        return this.rpc('/web/session/modules', {}).pipe(function(result) {
            var lang = self.user_context.lang,
                all_modules = _.uniq(self.module_list.concat(result));
            var params = { mods: all_modules, lang: lang};
            var to_load = _.difference(result, self.module_list).join(',');
            self.module_list = all_modules;

            var loaded = $.Deferred().resolve().promise();
            if (to_load.length) {
                loaded = $.when(
                    self.rpc('/web/webclient/csslist', {mods: to_load}, self.do_load_css),
                    self.rpc('/web/webclient/qweblist', {mods: to_load}).pipe(self.do_load_qweb),
                    self.rpc('/web/webclient/translations', params).pipe(function(trans) {
                        instance.web._t.database.set_bundle(trans);
                        var file_list = ["/web/static/lib/datejs/globalization/" + lang.replace("_", "-") + ".js"];
                        return self.rpc('/web/webclient/jslist', {mods: to_load}).pipe(function(files) {
                            return self.do_load_js(file_list.concat(files));
                        }).then(function () {
                            if (!Date.CultureInfo.pmDesignator) {
                                // If no am/pm designator is specified but the openerp
                                // datetime format uses %i, date.js won't be able to
                                // correctly format a date. See bug#938497.
                                Date.CultureInfo.amDesignator = 'AM';
                                Date.CultureInfo.pmDesignator = 'PM';
                            }
                        });
                    }))
            }
            return loaded.then(function() {
                self.on_modules_loaded();
                self.trigger('module_loaded');
                if (!no_session_valid_signal) {
                    self.on_session_valid();
                }
            });
        });
    },
    do_load_css: function (files) {
        var self = this;
        _.each(files, function (file) {
            $('head').append($('<link>', {
                'href': self.get_url(file),
                'rel': 'stylesheet',
                'type': 'text/css'
            }));
        });
    },
    do_load_js: function(files) {
        var self = this;
        var d = $.Deferred();
        if(files.length != 0) {
            var file = files.shift();
            var tag = document.createElement('script');
            tag.type = 'text/javascript';
            tag.src = self.get_url(file);
            tag.onload = tag.onreadystatechange = function() {
                if ( (tag.readyState && tag.readyState != "loaded" && tag.readyState != "complete") || tag.onload_done )
                    return;
                tag.onload_done = true;
                self.do_load_js(files).then(function () {
                    d.resolve();
                });
            };
            var head = document.head || document.getElementsByTagName('head')[0];
            head.appendChild(tag);
        } else {
            d.resolve();
        }
        return d;
    },
    do_load_qweb: function(files) {
        var self = this;
        _.each(files, function(file) {
            self.qweb_mutex.exec(function() {
                return self.rpc('/web/proxy/load', {path: file}).pipe(function(xml) {
                    if (!xml) { return; }
                    instance.web.qweb.add_template(_.str.trim(xml));
                });
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
            if(instance._openerp[mod] != undefined) {
                instance._openerp[mod](instance,instance[mod]);
                this.module_loaded[mod] = true;
            }
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
                         if (!this.contentDocument.body.childNodes[1]) {
                            options.error(this.contentDocument.body.childNodes);
                        }
                        else {
                            options.error(JSON.parse(this.contentDocument.body.childNodes[1].textContent));
                        }
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

        _(_.extend({}, options.data || {},
                   {session_id: this.session_id, token: token}))
            .each(function (value, key) {
                var $input = $form.find('[name=' + key +']');
                if (!$input.length) {
                    $input = $('<input type="hidden" name="' + key + '">')
                        .appendTo($form_data);
                }
                $input.val(value)
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
instance.web.bus = new (instance.web.Class.extend(instance.web.EventDispatcherMixin, {
    init: function() {
        instance.web.EventDispatcherMixin.init.call(this, parent);
        var self = this;
        // TODO fme: allow user to bind keys for some global actions.
        //           check gtk bindings
        // http://unixpapa.com/js/key.html
        _.each('click,dblclick,keydown,keypress,keyup'.split(','), function(evtype) {
            $('html').on(evtype, self, function(ev) {
                self.trigger(evtype, ev);
            });
        });
        _.each('resize,scroll'.split(','), function(evtype) {
            $(window).on(evtype, self, function(ev) {
                self.trigger(evtype, ev);
            });
        });
    }
}))();

/** OpenERP Translations */
instance.web.TranslationDataBase = instance.web.Class.extend(/** @lends instance.web.TranslationDataBase# */{
    /**
     * @constructs instance.web.TranslationDataBase
     * @extends instance.web.Class
     */
    init: function() {
        this.db = {};
        this.parameters = {"direction": 'ltr',
                        "date_format": '%m/%d/%Y',
                        "time_format": '%H:%M:%S',
                        "grouping": [],
                        "decimal_point": ".",
                        "thousands_sep": ","};
    },
    set_bundle: function(translation_bundle) {
        var self = this;
        this.db = {};
        var modules = _.keys(translation_bundle.modules);
        modules.sort();
        if (_.include(modules, "web")) {
            modules = ["web"].concat(_.without(modules, "web"));
        }
        _.each(modules, function(name) {
            self.add_module_translation(translation_bundle.modules[name]);
        });
        if (translation_bundle.lang_parameters) {
            this.parameters = translation_bundle.lang_parameters;
            this.parameters.grouping = py.eval(
                    this.parameters.grouping);
        }
    },
    add_module_translation: function(mod) {
        var self = this;
        _.each(mod.messages, function(message) {
            self.db[message.id] = message.string;
        });
    },
    build_translation_function: function() {
        var self = this;
        var fcnt = function(str) {
            var tmp = self.get(str);
            return tmp === undefined ? str : tmp;
        };
        fcnt.database = this;
        return fcnt;
    },
    get: function(key) {
        if (this.db[key])
            return this.db[key];
        return undefined;
    }
});

/** Custom jQuery plugins */
$.fn.getAttributes = function() {
    var o = {};
    if (this.length) {
        for (var attr, i = 0, attrs = this[0].attributes, l = attrs.length; i < l; i++) {
            attr = attrs.item(i)
            o[attr.nodeName] = attr.nodeValue;
        }
    }
    return o;
}

/** Jquery extentions */
$.Mutex = (function() {
    function Mutex() {
        this.def = $.Deferred().resolve();
    }
    Mutex.prototype.exec = function(action) {
        var current = this.def;
        var next = this.def = $.Deferred();
        return current.pipe(function() {
            return $.when(action()).always(function() {
                next.resolve();
            });
        });
    };
    return Mutex;
})();

$.async_when = function() {
    var async = false;
    var def = $.Deferred();
    $.when.apply($, arguments).then(function() {
        var args = arguments;
        var action = function() {
            def.resolve.apply(def, args);
        };
        if (async)
            action();
        else
            setTimeout(action, 0);
    }, function() {
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
	if (instance.connection.synch)
		return $.when.apply(this, arguments);
	else
		return old_async_when.apply(this, arguments);
};

/** Setup blockui */
if ($.blockUI) {
    $.blockUI.defaults.baseZ = 1100;
    $.blockUI.defaults.message = '<img src="/web/static/src/img/throbber2.gif">';
}

/** Setup default session */
instance.connection = new instance.web.Session();

/** Configure default qweb */
instance.web._t = new instance.web.TranslationDataBase().build_translation_function();
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
    return {toString: function () { return instance.web._t(s); }}
};
instance.web.qweb = new QWeb2.Engine();
instance.web.qweb.default_dict['__debug__'] = instance.connection.debug; // Which one ?
instance.web.qweb.debug = instance.connection.debug;
instance.web.qweb.default_dict = {
    '_' : _,
    '_t' : instance.web._t
};
instance.web.qweb.preprocess_node = function() {
    // Note that 'this' is the Qweb Node
    switch (this.node.nodeType) {
        case 3:
        case 4:
            // Text and CDATAs
            var translation = this.node.parentNode.attributes['t-translation'];
            if (translation && translation.value === 'off') {
                return;
            }
            var ts = _.str.trim(this.node.data);
            if (ts.length === 0) {
                return;
            }
            var tr = instance.web._t(ts);
            if (tr !== ts) {
                this.node.data = tr;
            }
            break;
        case 1:
            // Element
            var attr, attrs = ['label', 'title', 'alt', 'placeholder'];
            while (attr = attrs.pop()) {
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

instance.connection.on('module_loaded', this, function () {
    // provide timeago.js with our own translator method
    $.timeago.settings.translator = instance.web._t;
});

/**
 * Registry for all the client actions key: tag value: widget
 */
instance.web.client_actions = new instance.web.Registry();

/**
 * Client action to reload the whole interface.
 * If params has an entry 'menu_id', it opens the given menu entry.
 */
instance.web.Reload = instance.web.Widget.extend({
    init: function(parent, params) {
        this._super(parent);
        this.menu_id = (params && params.menu_id) || false;
    },
    start: function() {
        var l = window.location;
        var timestamp = new Date().getTime();
        var search = "?ts=" + timestamp;
        if (l.search) {
            search = l.search + "&ts=" + timestamp;
        } 
        var hash = l.hash;
        if (this.menu_id) {
            hash = "#menu_id=" + this.menu_id;
        }
        var url = l.protocol + "//" + l.host + l.pathname + search + hash;
        window.location = url;
    }
});
instance.web.client_actions.add("reload", "instance.web.Reload");

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
