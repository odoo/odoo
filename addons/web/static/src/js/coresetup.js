/*---------------------------------------------------------
 * OpenERP Web core
 *--------------------------------------------------------*/
var console;
if (!console) {
    // Even IE9 only exposes console object if debug window opened
    console = {};
    ('log error debug info warn assert clear dir dirxml trace group'
        + ' groupCollapsed groupEnd time timeEnd profile profileEnd count'
        + ' exception').split(/\s+/).forEach(function(property) {
            console[property] = _.identity;
    });
}

openerp.web.coresetup = function(instance) {

/** Session openerp specific RPC class */
instance.web.Session = instance.web.JsonRPC.extend( /** @lends instance.web.Session# */{
    init: function() {
        this._super.apply(this, arguments);
        // TODO: session store in cookie should be optional
        this.name = instance._session_id;
        this.qweb_mutex = new $.Mutex();
    },
    rpc: function(url, params, options) {
        params.session_id = this.session_id;
        return this._super(url, params, options);
    },
    /**
     * Setup a sessionm
     */
    session_bind: function(origin) {
        if (!_.isUndefined(this.origin)) {
            if (this.origin === origin) {
                return $.when();
            }
            throw new Error('Session already bound to ' + this.origin);
        }
        var self = this;
        this.setup(origin);
        instance.web.qweb.default_dict['_s'] = this.origin;
        this.session_id = false;
        this.uid = false;
        this.username = false;
        this.user_context= {};
        this.db = false;
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
        // TODO: session store in cookie should be optional
        this.session_id = this.get_cookie('session_id');
        return this.session_reload().then(function(result) {
            var modules = instance._modules.join(',');
            var deferred = self.rpc('/web/webclient/qweblist', {mods: modules}).then(self.load_qweb.bind(self));
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
    /**
     * (re)loads the content of a session: db name, username, user id, session
     * context and status of the support contract
     *
     * @returns {$.Deferred} deferred indicating the session is done reloading
     */
    session_reload: function () {
        var self = this;
        return this.rpc("/web/session/get_session_info", {}).done(function(result) {
            // If immediately follows a login (triggered by trying to restore
            // an invalid session or no session at all), refresh session data
            // (should not change, but just in case...)
            _.extend(self, result);
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
        return this.rpc("/web/session/authenticate", params).then(function(result) {
            if (!result.uid) {
                return $.Deferred().reject();
            }
            _.extend(self, result);
            if (!_volatile) {
                self.set_cookie('session_id', self.session_id);
            }
            return self.load_modules();
        });
    },
    session_logout: function() {
        this.set_cookie('session_id', '');
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
     */
    load_modules: function() {
        var self = this;
        return this.rpc('/web/session/modules', {}).then(function(result) {
            var all_modules = _.uniq(self.module_list.concat(result));
            var to_load = _.difference(result, self.module_list).join(',');
            self.module_list = all_modules;

            var loaded = self.load_translations();
            var datejs_locale = "/web/static/lib/datejs/globalization/" + self.user_context.lang.replace("_", "-") + ".js";

            var file_list = [ datejs_locale ];
            if(to_load.length) {
                loaded = $.when(
                    loaded,
                    self.rpc('/web/webclient/csslist', {mods: to_load}).done(self.load_css.bind(self)),
                    self.rpc('/web/webclient/qweblist', {mods: to_load}).then(self.load_qweb.bind(self)),
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
                if (!Date.CultureInfo.pmDesignator) {
                    // If no am/pm designator is specified but the openerp
                    // datetime format uses %i, date.js won't be able to
                    // correctly format a date. See bug#938497.
                    Date.CultureInfo.amDesignator = 'AM';
                    Date.CultureInfo.pmDesignator = 'PM';
                }
            });
        });
    },
    load_translations: function() {
        var params = { mods: this.module_list, lang: this.user_context.lang };
        return this.rpc('/web/webclient/translations', params).done(function(trans) {
            instance.web._t.database.set_bundle(trans);
        });
    },
    load_css: function (files) {
        var self = this;
        _.each(files, function (file) {
            $('head').append($('<link>', {
                'href': self.url(file, null),
                'rel': 'stylesheet',
                'type': 'text/css'
            }));
        });
    },
    load_js: function(files) {
        var self = this;
        var d = $.Deferred();
        if(files.length !== 0) {
            var file = files.shift();
            var tag = document.createElement('script');
            tag.type = 'text/javascript';
            tag.src = self.url(file, null);
            tag.onload = tag.onreadystatechange = function() {
                if ( (tag.readyState && tag.readyState != "loaded" && tag.readyState != "complete") || tag.onload_done )
                    return;
                tag.onload_done = true;
                self.load_js(files).done(function () {
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
    load_qweb: function(files) {
        var self = this;
        _.each(files, function(file) {
            self.qweb_mutex.exec(function() {
                return self.rpc('/web/proxy/load', {path: file}).then(function(xml) {
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
})
instance.web.bus = new instance.web.Bus();

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
$.Mutex = (function() {
    function Mutex() {
        this.def = $.Deferred().resolve();
    }
    Mutex.prototype.exec = function(action) {
        var current = this.def;
        var next = this.def = $.Deferred();
        return current.then(function() {
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
instance.web.qweb.debug = instance.session.debug;
instance.web.qweb.default_dict = {
    '_' : _,
    '_t' : instance.web._t,
    'JSON': JSON,
    '__debug__': instance.session.debug,
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
            var match = /^(\s*)(.+?)(\s*)$/.exec(this.node.data);
            if (match) {
                this.node.data = match[1] + instance.web._t(match[2]) + match[3];
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
}
instance.web.unblockUI = function() {
    _.each(instance.web.Throbber.throbbers, function(el) {
        el.destroy();
    });
    return $.unblockUI.apply($, arguments);
}

/**
 * Registry for all the client actions key: tag value: widget
 */
instance.web.client_actions = new instance.web.Registry();

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
