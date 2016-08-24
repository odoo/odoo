odoo.define('web.Session', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var utils = require('web.utils');

var _t = core._t;
var qweb = core.qweb;
var mixins = core.mixins;

var Session = core.Class.extend(mixins.EventDispatcherMixin, {
    /**

    @param parent The parent of the newly created object.
    or `null` if the server to contact is the origin server.
    @param {Dict} options A dictionary that can contain the following options:

        * "override_session": Default to false. If true, the current session object will
          not try to re-use a previously created session id stored in a cookie.
        * "session_id": Default to null. If specified, the specified session_id will be used
          by this session object. Specifying this option automatically implies that the option
          "override_session" is set to true.
     */
    init: function(parent, origin, options) {
        mixins.EventDispatcherMixin.init.call(this, parent);
        options = options || {};
        this.module_list = (options.modules && options.modules.slice()) || (window.odoo._modules && window.odoo._modules.slice()) || [];
        this.server = null;
        this.session_id = options.session_id || null;
        this.override_session = options.override_session || !!options.session_id || false;
        this.avoid_recursion = false;
        this.use_cors = options.use_cors || false;
        this.setup(origin);
        this.debug = ($.deparam($.param.querystring()).debug !== undefined);

        // for historic reasons, the session requires a name to properly work
        // (see the methods get_cookie and set_cookie).  We should perhaps
        // remove it totally (but need to make sure the cookies are properly set)
        this.name = "instance0";
        // TODO: session store in cookie should be optional
        this.qweb_mutex = new utils.Mutex();
        this.currencies = {};
        this._groups_def = {};
    },
    setup: function(origin, options) {
        // must be able to customize server
        var window_origin = location.protocol + "//" + location.host;
        origin = origin ? origin.replace( /\/+$/, '') : window_origin;
        if (!_.isUndefined(this.origin) && this.origin !== origin)
            throw new Error('Session already bound to ' + this.origin);
        else
            this.origin = origin;
        this.prefix = this.origin;
        this.server = this.origin; // keep chs happy
        this.origin_server = this.origin === window_origin;
        options = options || {};
        if ('use_cors' in options) {
            this.use_cors = options.use_cors;
        }
    },
    /**
     * Setup a session
     */
    session_bind: function(origin) {
        var self = this;
        this.setup(origin);
        qweb.default_dict._s = this.origin;
        this.uid = null;
        this.username = null;
        this.user_context= {};
        this.db = null;
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
        return this.session_reload().then(function() {
            var modules = self.module_list.join(',');
            var deferred = self.load_qweb(modules);
            if(self.session_is_valid()) {
                return deferred.then(function() { return self.load_modules(); });
            }
            return $.when(
                    deferred,
                    self.rpc('/web/webclient/bootstrap_translations', {mods: self.module_list}).then(function(trans) {
                        _t.database.set_bundle(trans);
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
        return $.when(this._session_authenticate.apply(this, arguments)).then(function() {
            return self.load_modules();
        });
    },
    /**
     * The session is validated either by login or by restoration of a previous session
     */
    _session_authenticate: function(db, login, password) {
        var self = this;
        var params = {db: db, login: login, password: password};
        return this.rpc("/web/session/authenticate", params).then(function(result) {
            if (!result.uid) {
                return $.Deferred().reject();
            }
            delete result.session_id;
            _.extend(self, result);
        });
    },
    session_logout: function() {
        $.bbq.removeState();
        return this.rpc("/web/session/destroy", {});
    },
    user_has_group: function(group) {
        if (!this.uid) {
            return $.when().resolve(false);
        }
        var def = this._groups_def[group];
        if (!def) {
            var Model = window.openerp.web.Model;
            var Users = new Model('res.users');
            def = this._groups_def[group] = Users.call('has_group', [group]);
        }
        return def;
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
        utils.set_cookie(this.name + '|' + name, value, ttl);
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

            var loaded = $.when(self.load_currencies(), self.load_translations());
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
    load_currencies: function() {
        this.currencies = {};
        var self = this;
        return new openerp.web.Model("res.currency").query(["symbol", "position", "decimal_places"]).all()
                .then(function(value) {
                    _.each(value, function(k){
                        self.currencies[k.id] = {'symbol': k.symbol, 'position': k.position, 'digits': [69,k.decimal_places]};
                    });
                });
    },
    load_translations: function() {
        return _t.database.load_translations(this, this.module_list, this.user_context.lang);
    },
    load_css: function (files) {
        var self = this;
        _.each(files, function (file) {
            ajax.loadCSS(self.url(file, null));
        });
    },
    load_js: function(files) {
        var self = this;
        var d = $.Deferred();
        if (files.length !== 0) {
            var file = files.shift();
            var url = self.url(file, null);
            ajax.loadJS(url).done(d.resolve);
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
                qweb.add_template(_.str.trim(xml));
            });
        });
        return self.qweb_mutex.def;
    },
    on_modules_loaded: function() {
        var openerp = window.openerp;
        for(var j=0; j<this.module_list.length; j++) {
            var mod = this.module_list[j];
            if(this.module_loaded[mod])
                continue;
            openerp[mod] = {};
            // init module mod
            var fct = openerp._openerp[mod];
            if(typeof(fct) === "function") {
                openerp._openerp[mod] = {};
                for (var k in fct) {
                    openerp._openerp[mod][k] = fct[k];
                }
                fct(openerp, openerp._openerp[mod]);
            }
            this.module_loaded[mod] = true;
        }
    },
    get_currency: function(currency_id) {
        return this.currencies[currency_id];
    },
    get_file: function (options) {
        if (this.override_session){
            options.data.session_id = this.session_id;
        }
        options.session = this;
        ajax.get_file(options);
    },
    synchronized_mode: function(to_execute) {
        var synch = this.synch;
        this.synch = true;
        try {
            return to_execute();
        } finally {
            this.synch = synch;
        }
    },
    /**
     * (re)loads the content of a session: db name, username, user id, session
     * context and status of the support contract
     *
     * @returns {$.Deferred} deferred indicating the session is done reloading
     */
    session_reload: function () {
        var self = this;
        return self.rpc("/web/session/get_session_info", {}).then(function(result) {
            delete result.session_id;
            _.extend(self, result);
        });
    },
    check_session_id: function() {
        var self = this;
        if (this.avoid_recursion)
            return $.when();
        if (this.session_id)
            return $.when(); // we already have the session id
        if (!this.use_cors && (this.override_session || ! this.origin_server)) {
            // If we don't use the origin server we consider we should always create a new session.
            // Even if some browsers could support cookies when using jsonp that behavior is
            // not consistent and the browser creators are tending to removing that feature.
            this.avoid_recursion = true;
            return this.rpc("/gen_session_id", {}).then(function(result) {
                self.session_id = result;
            }).always(function() {
                self.avoid_recursion = false;
            });
        } else {
            // normal use case, just use the cookie
            self.session_id = utils.get_cookie("session_id");
            return $.when();
        }
    },
    /**
     * Executes an RPC call, registering the provided callbacks.
     *
     * Registers a default error callback if none is provided, and handles
     * setting the correct session id and session context in the parameter
     * objects
     *
     * @param {String} url RPC endpoint
     * @param {Object} params call parameters
     * @param {Object} options additional options for rpc call
     * @param {Function} success_callback function to execute on RPC call success
     * @param {Function} error_callback function to execute on RPC call failure
     * @returns {jQuery.Deferred} jquery-provided ajax deferred
     */
    rpc: function(url, params, options) {
        var self = this;
        options = _.clone(options || {});
        var shadow = options.shadow || false;
        options.headers = _.extend({}, options.headers)
        if (odoo.debug) {
            options.headers["X-Debug-Mode"] = true;
        }

        delete options.shadow;

        return self.check_session_id().then(function() {
            // TODO: remove
            if (! _.isString(url)) {
                _.extend(options, url);
                url = url.url;
            }
            // TODO correct handling of timeouts
            if (! shadow)
                self.trigger('request');
            var fct;
            if (self.origin_server) {
                fct = ajax.jsonRpc;
                if (self.override_session) {
                    options.headers["X-Openerp-Session-Id"] = self.session_id || '';
                }
            } else if (self.use_cors) {
                fct = ajax.jsonRpc;
                url = self.url(url, null);
                options.session_id = self.session_id || '';
                if (self.override_session) {
                    options.headers["X-Openerp-Session-Id"] = self.session_id || '';
                }
            } else {
                fct = ajax.jsonpRpc;
                url = self.url(url, null);
                options.session_id = self.session_id || '';
            }
            var p = fct(url, "call", params, options);
            p = p.then(function (result) {
                if (! shadow)
                    self.trigger('response');
                return result;
            }, function(type, error, textStatus, errorThrown) {
                if (type === "server") {
                    if (! shadow)
                        self.trigger('response');
                    if (error.code === 100) {
                        self.uid = false;
                    }
                    return $.Deferred().reject(error, $.Event());
                } else {
                    if (! shadow)
                        self.trigger('response_failed');
                    var nerror = {
                        code: -32098,
                        message: "XmlHttpRequestError " + errorThrown,
                        data: {type: "xhr"+textStatus, debug: error.responseText, objects: [error, errorThrown] }
                    };
                    return $.Deferred().reject(nerror, $.Event());
                }
            });
            return p.fail(function() { // Allow deferred user to disable rpc_error call in fail
                p.fail(function(error, event) {
                    if (!event.isDefaultPrevented()) {
                        self.trigger('error', error, event);
                    }
                });
            });
        });
    },
    url: function(path, params) {
        params = _.extend(params || {});
        if (this.override_session || (! this.origin_server))
            params.session_id = this.session_id;
        var qs = $.param(params);
        if (qs.length > 0)
            qs = "?" + qs;
        var prefix = _.any(['http://', 'https://', '//'], function(el) {
            return path.length >= el.length && path.slice(0, el.length) === el;
        }) ? '' : this.prefix;
        return prefix + path + qs;
    },
});

return Session;

});


odoo.define('web.config', function (require) {
"use strict";

var bus = require('web.core').bus;
// Configuration module.
// To do: refactor session, and this module in a sane way.  Session accomplish
// several concerns (rpc, configuration, currencies (wtf?), user permissions, ...)
// they should be clarified and separated.

var medias = [
    window.matchMedia('(max-width: 767px)'),
    window.matchMedia('(min-width: 768px) and (max-width: 991px)'),
    window.matchMedia('(min-width: 992px) and (max-width: 1199px)'),
    window.matchMedia('(min-width: 1200px)')
];
_.each(medias, function(m) {
    m.addListener(set_size_class);
});

var config = {
    debug: ($.deparam($.param.querystring()).debug !== undefined),
    device: {
        touch: 'ontouchstart' in window || 'onmsgesturechange' in window,
        size_class: size_class(),
        SIZES: { XS: 0, SM: 1, MD: 2, LG: 3 },
    },
};

function size_class() {
    for(var i = 0 ; i < medias.length ; i++) {
        if(medias[i].matches) {
            return i;
        }
    }
}
function set_size_class() {
    var sc = size_class();
    if (sc !== config.device.size_class) {
        config.device.size_class = sc;
        bus.trigger('size_class', sc);
    }
}

return config;
});
