odoo.define('web.Session', function (require) {
"use strict";

var ajax = require('web.ajax');
var concurrency = require('web.concurrency');
var core = require('web.core');
var mixins = require('web.mixins');
var utils = require('web.utils');

var _t = core._t;
var qweb = core.qweb;

// To do: refactor session. Session accomplishes several concerns (rpc,
// configuration, currencies (wtf?), user permissions...). They should be
// clarified and separated.

var Session = core.Class.extend(mixins.EventDispatcherMixin, {
    /**

    @param parent The parent of the newly created object.
    or `null` if the server to contact is the origin server.
    @param {Dict} options A dictionary that can contain the following options:

        * "modules"
        * "use_cors"
     */
    init: function (parent, origin, options) {
        mixins.EventDispatcherMixin.init.call(this);
        this.setParent(parent);
        options = options || {};
        this.module_list = (options.modules && options.modules.slice()) || (window.odoo._modules && window.odoo._modules.slice()) || [];
        this.server = null;
        this.avoid_recursion = false;
        this.use_cors = options.use_cors || false;
        this.setup(origin);

        // for historic reasons, the session requires a name to properly work
        // (see the methods get_cookie and set_cookie).  We should perhaps
        // remove it totally (but need to make sure the cookies are properly set)
        this.name = "instance0";
        // TODO: session store in cookie should be optional
        this.qweb_mutex = new concurrency.Mutex();
        this.currencies = {};
        this._groups_def = {};
        core.bus.on('invalidate_session', this, this._onInvalidateSession);
    },
    setup: function (origin, options) {
        // must be able to customize server
        var window_origin = location.protocol + "//" + location.host;
        origin = origin ? origin.replace( /\/+$/, '') : window_origin;
        if (!_.isUndefined(this.origin) && this.origin !== origin)
            throw new Error('Session already bound to ' + this.origin);
        else
            this.origin = origin;
        this.prefix = this.origin;
        this.server = this.origin; // keep chs happy
        options = options || {};
        if ('use_cors' in options) {
            this.use_cors = options.use_cors;
        }
    },
    /**
     * Setup a session
     */
    session_bind: function (origin) {
        this.setup(origin);
        qweb.default_dict._s = this.origin;
        this.uid = null;
        this.username = null;
        this.user_context= {};
        this.db = null;
        this.active_id = null;
        return this.session_init();
    },
    /**
     * Init a session, reloads from cookie, if it exists
     */
    session_init: function () {
        var self = this;
        var prom = this.session_reload();

        if (this.is_frontend) {
            return prom.then(function () {
                return self.load_translations();
            });
        }

        return prom.then(function () {
            var modules = self.module_list.join(',');
            var promise = self.load_qweb(modules);
            if (self.session_is_valid()) {
                return promise.then(function () { return self.load_modules(); });
            }
            return Promise.all([
                    promise,
                    self.rpc('/web/webclient/bootstrap_translations', {mods: self.module_list})
                        .then(function (trans) {
                            _t.database.set_bundle(trans);
                        })
                    ]);
        });
    },
    session_is_valid: function () {
        var db = $.deparam.querystring().db;
        if (db && this.db !== db) {
            return false;
        }
        return !!this.uid;
    },
    /**
     * The session is validated by restoration of a previous session
     */
    session_authenticate: function () {
        var self = this;
        return Promise.resolve(this._session_authenticate.apply(this, arguments)).then(function () {
            return self.load_modules();
        });
    },
    /**
     * The session is validated either by login or by restoration of a previous session
     */
    _session_authenticate: function (db, login, password) {
        var self = this;
        var params = {db: db, login: login, password: password};
        return this.rpc("/web/session/authenticate", params).then(function (result) {
            if (!result.uid) {
                return Promise.reject();
            }
            _.extend(self, result);
        });
    },
    session_logout: function () {
        $.bbq.removeState();
        return this.rpc("/web/session/destroy", {});
    },
    user_has_group: function (group) {
        if (!this.uid) {
            return Promise.resolve(false);
        }
        var def = this._groups_def[group];
        if (!def) {
            def = this._groups_def[group] = this.rpc('/web/dataset/call_kw/res.users/has_group', {
                "model": "res.users",
                "method": "has_group",
                "args": [group],
                "kwargs": {}
            });
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
    load_modules: function () {
        var self = this;
        var modules = odoo._modules;
        var all_modules = _.uniq(self.module_list.concat(modules));
        var to_load = _.difference(modules, self.module_list).join(',');
        this.module_list = all_modules;

        var loaded = Promise.resolve(self.load_translations());
        var locale = "/web/webclient/locale/" + self.user_context.lang || 'en_US';
        var file_list = [ locale ];
        if(to_load.length) {
            loaded = Promise.all([
                loaded,
                self.rpc('/web/webclient/csslist', {mods: to_load})
                    .then(self.load_css.bind(self)),
                self.load_qweb(to_load),
                self.rpc('/web/webclient/jslist', {mods: to_load})
                    .then(function (files) {
                        file_list = file_list.concat(files);
                    })
            ]);
        }
        return loaded.then(function () {
            return self.load_js(file_list);
        }).then(function () {
            self._configureLocale();
        });
    },
    load_translations: function () {
        /* We need to get the website lang at this level.
           The only way is to get it is to take the HTML tag lang
           Without it, we will always send undefined if there is no lang
           in the user_context. */
        var html = document.documentElement,
            htmlLang = (html.getAttribute('lang') || 'en_US').replace('-', '_'),
            lang = this.user_context.lang || htmlLang;

        return _t.database.load_translations(this, this.module_list, lang, this.translationURL);
    },
    load_css: function (files) {
        var self = this;
        _.each(files, function (file) {
            ajax.loadCSS(self.url(file, null));
        });
    },
    load_js: function (files) {
        var self = this;
        return new Promise(function (resolve, reject) {
            if (files.length !== 0) {
                var file = files.shift();
                var url = self.url(file, null);
                ajax.loadJS(url).then(resolve);
            } else {
                resolve();
            }
        });
    },
    load_qweb: function (mods) {
        var self = this;
        var lock = this.qweb_mutex.exec(function () {
            var cacheId = self.cache_hashes && self.cache_hashes.qweb;
            var route  = '/web/webclient/qweb/' + (cacheId ? cacheId : Date.now()) + '?mods=' + mods;
            return $.get(route).then(function (doc) {
                if (!doc) { return; }
                const owlTemplates = [];
                for (let child of doc.querySelectorAll("templates > [owl]")) {
                    child.removeAttribute('owl');
                    owlTemplates.push(child.outerHTML);
                    child.remove();
                }
                qweb.add_template(doc);
                self.owlTemplates = `<templates> ${owlTemplates.join('\n')} </templates>`;
            });
        });
        return lock;
    },
    get_currency: function (currency_id) {
        return this.currencies[currency_id];
    },
    get_file: function (options) {
        options.session = this;
        return ajax.get_file(options);
    },
    /**
     * (re)loads the content of a session: db name, username, user id, session
     * context and status of the support contract
     *
     * @returns {Promise} promise indicating the session is done reloading
     */
    session_reload: function () {
        var result = _.extend({}, window.odoo.session_info);
        _.extend(this, result);
        return Promise.resolve();
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
     * @returns {Promise}
     */
    rpc: function (url, params, options) {
        var self = this;
        options = _.clone(options || {});
        options.headers = _.extend({}, options.headers);

        // we add here the user context for ALL queries, mainly to pass
        // the allowed_company_ids key
        if (params && params.kwargs) {
            params.kwargs.context = _.extend(params.kwargs.context || {}, this.user_context);
        }

        // TODO: remove
        if (! _.isString(url)) {
            _.extend(options, url);
            url = url.url;
        }
        if (self.use_cors) {
            url = self.url(url, null);
        }

        return ajax.jsonRpc(url, "call", params, options);
    },
    url: function (path, params) {
        params = _.extend(params || {});
        var qs = $.param(params);
        if (qs.length > 0)
            qs = "?" + qs;
        var prefix = _.any(['http://', 'https://', '//'], function (el) {
            return path.length >= el.length && path.slice(0, el.length) === el;
        }) ? '' : this.prefix;
        return prefix + path + qs;
    },
    /**
     * Returns the time zone difference (in minutes) from the current locale
     * (host system settings) to UTC, for a given date. The offset is positive
     * if the local timezone is behind UTC, and negative if it is ahead.
     *
     * @param {string | moment} date a valid string date or moment instance
     * @returns {integer}
     */
    getTZOffset: function (date) {
        return -new Date(date).getTimezoneOffset();
    },
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * Replaces the value of a key in cache_hashes (the hash of some resource computed on the back-end by a unique value
     * @param {string} key the key in the cache_hashes to invalidate
     */
    invalidateCacheKey: function(key) {
        if (this.cache_hashes && this.cache_hashes[key]) {
            this.cache_hashes[key] = Date.now();
        }
    },

    /**
     * Reload the currencies (initially given in session_info). This is meant to
     * be called when changes are made on 'res.currency' records (e.g. when
     * (de-)activating a currency). For the sake of simplicity, we reload all
     * session_info.
     *
     * FIXME: this whole currencies handling should be moved out of session.
     *
     * @returns {$.promise}
     */
    reloadCurrencies: function () {
        var self = this;
        return this.rpc('/web/session/get_session_info').then(function (result) {
            self.currencies = result.currencies;
        });
    },

    setCompanies: function (main_company_id, company_ids) {
        var hash = $.bbq.getState()
        hash.cids = company_ids.sort(function(a, b) {
            if (a === main_company_id) {
                return -1;
            } else if (b === main_company_id) {
                return 1;
            } else {
                return a - b;
            }
        }).join(',');
        utils.set_cookie('cids', hash.cids || String(main_company_id));
        $.bbq.pushState({'cids': hash.cids}, 0);
        location.reload();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Sets first day of week in current locale according to the user language.
     *
     * @private
     */
    _configureLocale: function () {
        moment.updateLocale(moment.locale(), {
            week: {
                dow: (_t.database.parameters.week_start || 0) % 7,
            },
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onInvalidateSession: function () {
        this.uid = false;
    },
});

return Session;

});
