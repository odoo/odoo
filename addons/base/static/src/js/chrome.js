/*---------------------------------------------------------
 * OpenERP base library
 *---------------------------------------------------------*/

openerp.base.chrome = function(openerp) {

openerp.base.callback = function(obj, method) {
    var callback = function() {
        var args = Array.prototype.slice.call(arguments);
        var r;
        for(var i = 0; i < callback.callback_chain.length; i++)  {
            var c = callback.callback_chain[i];
            if(c.unique) {
                // al: obscure but shortening C-style hack, sorry
                callback.callback_chain.pop(i--);
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
 * Base error for lookup failure
 *
 * @class
 */
openerp.base.NotFound = Class.extend( /** @lends openerp.base.NotFound# */ {
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
openerp.base.Registry = Class.extend( /** @lends openerp.base.Registry# */ {
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
    }
});

openerp.base.BasicController = Class.extend( /** @lends openerp.base.BasicController# */{
    /**
     * rpc operations, event binding and callback calling should be done in
     * start() instead of init so that event can be hooked in between.
     *
     *  @constructs
     */
    init: function(element_id) {
        this.element_id = element_id;
        this.$element = $('#' + element_id);
        openerp.screen[element_id] = this;

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
     * Controller start
     * event binding, rpc and callback calling required to initialize the
     * object can happen here
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
    on_ready: function() {
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
        if(true || window.openerp.debug || (window.location.search.indexOf('?debug') !== -1)) {
            if(window.console) {
                console.log(arguments);
            } else {
                $.each(arguments, function(i,v) {
                    v = v==null ? "null" : v;
                    $('<pre></pre>').text(v.toString()).appendTo($('body'));
                });
            }
        }

    }
});

openerp.base.Session = openerp.base.BasicController.extend( /** @lends openerp.base.Session# */{
    /**
     * @constructs
     * @extends openerp.base.BasicController
     * @param element_id to use for exception reporting
     * @param server
     * @param port
     */
    init: function(element_id, server, port) {
        this._super(element_id);
        this.server = (server == undefined) ? location.hostname : server;
        this.port = (port == undefined) ? location.port : port;
        this.rpc_mode = (server == location.hostname) ? "ajax" : "jsonp";
        this.debug = true;
        this.db = "";
        this.login = "";
        this.password = "";
        this.uid = false;
        this.session_id = false;
        this.module_list = [];
        this.module_loaded = {"base": true};
        this.context = {};
    },
    start: function() {
        this.session_restore();
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
     * @param {Function} success_callback function to execute on RPC call success
     * @param {Function} error_callback function to execute on RPC call failure
     * @returns {jQuery.Deferred} jquery-provided ajax deferred
     */
    rpc: function(url, params, success_callback, error_callback) {
        // Construct a JSON-RPC2 request, method is currently unused
        params.session_id = this.session_id;
        params.context = typeof(params.context) != "undefined" ? params.context  : this.context;

        // Use a default error handler unless defined
        error_callback = typeof(error_callback) != "undefined" ? error_callback : this.on_rpc_error;

        // Call using the rpc_mode
        return this.rpc_ajax(url, {
            jsonrpc: "2.0",
            method: "call",
            params: params,
            id:null
        }, success_callback, error_callback);
    },
    /**
     * Raw JSON-RPC call
     *
     * @returns {jQuery.Deferred} ajax-based deferred object
     */
    rpc_ajax: function(url, payload, success_callback, error_callback) {
        var self = this;
        this.on_rpc_request();
        // url can be an $.ajax option object
        if (_.isString(url)) {
            url = {
                url: url
            }
        }
        var ajax = _.extend({
            type: "POST",
            url: url,
            dataType: 'json',
            contentType: 'application/json',
            data: JSON.stringify(payload),
            processData: false,
            success: function(response, textStatus, jqXHR) {
                self.on_rpc_response();
                if (response.error) {
                    if (response.error.data.type == "session_invalid") {
                        self.uid = false;
                        self.on_session_invalid(function() {
                            self.rpc(url, payload.params, success_callback, error_callback);
                        });
                    } else {
                        error_callback(response.error);
                    }
                } else {
                    success_callback(response["result"], textStatus, jqXHR);
                }
            },
            error: function(jqXHR, textStatus, errorThrown) {
                self.on_rpc_response();
                var error = {
                    code: -32098,
                    message: "XmlHttpRequestError " + errorThrown,
                    data: {type: "xhr"+textStatus, debug: jqXHR.responseText, objects: [jqXHR, errorThrown] }
                };
                error_callback(error);
            }
        }, url);
        return $.ajax(ajax);
    },
    on_rpc_request: function() {
    },
    on_rpc_response: function() {
    },
    on_rpc_error: function(error) {
        this.on_log(error.message, error.data.debug);
    },
    /**
     * The session is validated either by login or by restoration of a previous session
     */
    on_session_valid: function() {
        if(!openerp._modules_loaded)
            this.load_modules();
    },
    on_session_invalid: function(contination) {
    },
    session_is_valid: function() {
        return this.uid;
    },
    session_login: function(db, login, password, success_callback) {
        var self = this;
        this.db = db;
        this.login = login;
        this.password = password;
        var params = { db: this.db, login: this.login, password: this.password };
        this.rpc("/base/session/login", params, function(result) {
            self.session_id = result.session_id;
            self.uid = result.uid;
            self.session_save();
            self.on_session_valid();
            if (success_callback)
                success_callback();
        });
    },
    session_logout: function() {
        this.uid = false;
    },
    /**
     * Reloads uid and session_id from local storage, if they exist
     */
    session_restore: function () {
        this.uid = this.get_cookie('uid');
        this.session_id = this.get_cookie('session_id');
        // we should do an rpc to confirm that this session_id is valid and if it is retrieve the information about db and login
        // then call on_session_valid
        this.on_session_valid();
    },
    /**
     * Saves the session id and uid locally
     */
    session_save: function () {
        this.set_cookie('uid', this.uid);
        this.set_cookie('session_id', this.session_id);
    },
    /**
     * Fetches a cookie stored by an openerp session
     *
     * @private
     * @param name the cookie's name
     */
    get_cookie: function (name) {
        var nameEQ = this.element_id + '|' + name + '=';
        var cookies = document.cookie.split(';');
        for(var i=0; i<cookies.length; ++i) {
            var cookie = cookies[i].replace(/^\s*/, '');
            if(cookie.indexOf(nameEQ) === 0) {
                return decodeURIComponent(cookie.substring(nameEQ.length));
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
        ttl = ttl || 24*60*60*365;
        document.cookie = [
            this.element_id + '|' + name + '=' + encodeURIComponent(value),
            'max-age=' + ttl,
            'expires=' + new Date(new Date().getTime() + ttl*1000).toGMTString()
        ].join(';');
    },
    /**
     * Load additional web addons of that instance and init them
     */
    load_modules: function() {
        var self = this;
        this.rpc('/base/session/modules', {}, function(result) {
            self.module_list = result['modules'];
            self.rpc('/base/session/jslist', {"mods": self.module_list.join(',')}, self.debug ? self.do_load_modules_debug : self.do_load_modules_prod);
            openerp._modules_loaded = true;
        });
    },
    do_load_modules_debug: function(result) {
        $LAB.setOptions({AlwaysPreserveOrder: true})
            .script(result.files)
            .wait(this.on_modules_loaded);
    },
    do_load_modules_prod: function() {
        // load merged ones
        // /base/session/css?mod=mod1,mod2,mod3
        // /base/session/js?mod=mod1,mod2,mod3
        // use $.getScript(‘your_3rd_party-script.js’); ? i want to keep lineno !
    },
    on_modules_loaded: function() {
        var self = this;
        for(var j=0; j<self.module_list.length; j++) {
            var mod = self.module_list[j];
            if(self.module_loaded[mod])
                continue;
            openerp[mod] = {};
            // init module mod
            openerp._openerp[mod](openerp);
            self.module_loaded[mod] = true;
        }
    }
});

openerp.base.Controller = openerp.base.BasicController.extend( /** @lends openerp.base.Controller# */{
    /**
     * @constructs
     * @extends openerp.base.BasicController
     */
    init: function(session, element_id) {
        this._super(element_id);
        this.session = session;
    },
    on_log: function() {
        if(this.session)
            this.session.log.apply(this.session,arguments);
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
        // TODO: support additional arguments ?
        return this.session.rpc(url, data, success, error);
    }
});

openerp.base.CrashManager = openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
        this.session.on_rpc_error.add(this.on_rpc_error);
    },
    on_rpc_error: function(error) {
        var msg = error.message + "\n" + error.data.debug;
        this.display_error(msg);
    },
    display_error: function(message) {
        $('<pre></pre>').text(message).dialog({
            modal: true,
            buttons: {
                OK: function() {
                    $(this).dialog("close");
                }
            }
        });
    }
});

openerp.base.Database = openerp.base.Controller.extend({
// Non Session Controller to manage databases
});

openerp.base.Loading =  openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
        this.count = 0;
        this.session.on_rpc_request.add_first(this.on_rpc_event, 1);
        this.session.on_rpc_response.add_last(this.on_rpc_event, -1);
    },
    on_rpc_event : function(increment) {
        this.count += increment;
        if (this.count) {
            //this.$element.html(QWeb.render("Loading", {}));
            this.$element.html("Loading ("+this.count+")");
            this.$element.show();
        } else {
            this.$element.fadeOut();
        }
    }
});

openerp.base.Notification =  openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
        this.$element.notify({
            speed: 500,
            expires: 1500
        });
    },
    'default': function(title, text) {
        this.$element.notify('create', {
            title: title,
            text: text
        });
    },
    alert: function(title, text) {
        this.$element.notify('create', 'oe_notification_alert', {
            title: title,
            text: text
        });
    }
});

openerp.base.Login =  openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
    },
    start: function() {
        this.$element.html(QWeb.render("Login", {}));
        this.$element.find("form").submit(this.on_submit);
    },
    on_login_invalid: function() {
        this.$element
            .removeClass("login_valid")
            .addClass("login_invalid")
            .show();
    },
    on_login_valid: function() {
        this.$element
            .removeClass("login_invalid")
            .addClass("login_valid")
            .hide();
    },
    on_submit: function(ev) {
        ev.preventDefault();
        var self = this;
        var $e = this.$element;
        var db = $e.find("form input[name=db]").val();
        var login = $e.find("form input[name=login]").val();
        var password = $e.find("form input[name=password]").val();
        //$e.hide();
        // Should hide then call callback
        this.session.session_login(db, login, password, function() {
            if(self.session.session_is_valid()) {
                self.on_login_valid();
            } else {
                self.on_login_invalid();
            }
        });
    },
    do_ask_login: function(continuation) {
        this.on_login_invalid();
        this.on_login_valid.add({
            position: "last",
            unique: true,
            callback: continuation
        });
    }
});

openerp.base.Header =  openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
    },
    start: function() {
        this.do_update();
    },
    do_update: function() {
        this.$element.html(QWeb.render("Header", this));
    }
});

openerp.base.Menu =  openerp.base.Controller.extend({
    init: function(session, element_id, secondary_menu_id) {
        this._super(session, element_id);
        this.secondary_menu_id = secondary_menu_id;
        this.$secondary_menu = $("#" + secondary_menu_id);
        this.menu = false;
    },
    start: function() {
        this.rpc("/base/menu/load", {}, this.on_loaded);
    },
    on_loaded: function(data) {
        this.data = data;
        this.$element.html(QWeb.render("Menu", this.data));
        for (var i = 0; i < this.data.data.children.length; i++) {
            var v = { menu : this.data.data.children[i] };
            this.$secondary_menu.append(QWeb.render("Menu.secondary", v));
        }
        this.$secondary_menu.find("div.menu_accordion").accordion({
            animated : false,
            autoHeight : false,
            icons : false
        });
        this.$secondary_menu.find("div.submenu_accordion").accordion({
            animated : false,
            autoHeight : false,
            active: false,
            collapsible: true,
            header: 'h4'
        });

        this.$element.add(this.$secondary_menu).find("a").click(this.on_menu_click);
        this.on_ready();
    },
    on_menu_click: function(ev, id) {
        id = id || 0;
        var $menu, $parent, $secondary;

        if (id) {
            // We can manually activate a menu with it's id (for hash url mapping)
            $menu = this.$element.find('a[data-menu=' + id + ']');
            if (!$menu.length) {
                $menu = this.$secondary_menu.find('a[data-menu=' + id + ']');
            }
        } else {
            $menu = $(ev.currentTarget);
            id = $menu.data('menu');
        }
        if (this.$secondary_menu.has($menu).length) {
            $secondary = $menu.parents('.menu_accordion');
            $parent = this.$element.find('a[data-menu=' + $secondary.data('menu-parent') + ']');
        } else {
            $parent = $menu;
            $secondary = this.$secondary_menu.find('.menu_accordion[data-menu-parent=' + $menu.attr('data-menu') + ']');
        }

        this.$secondary_menu.find('.menu_accordion').hide();
        // TODO: ui-accordion : collapse submenus and expand the good one
        $secondary.show();

        if (id) {
            this.rpc('/base/menu/action', {'menu_id': id},
                    this.on_menu_action_loaded);
        }

        $('.active', this.$element.add(this.$secondary_menu)).removeClass('active');
        $parent.addClass('active');
        $menu.addClass('active');
        $menu.parent('h4').addClass('active');

        return !$menu.is(".leaf");
    },
    on_menu_action_loaded: function(data) {
        var self = this;
        if (data.action.length) {
            var action = data.action[0][2];
            self.on_action(action);
        }
    },
    on_action: function(action) {
    }
});

openerp.base.Homepage = openerp.base.Controller.extend({
});

openerp.base.Preferences = openerp.base.Controller.extend({
});

openerp.base.ImportExport = openerp.base.Controller.extend({
});

openerp.base.WebClient = openerp.base.Controller.extend({
    init: function(element_id) {
        var self = this;
        this._super(null, element_id);

        QWeb.add_template("xml/base.xml");
        this.$element.html(QWeb.render("Interface", {}));

        this.session = new openerp.base.Session("oe_errors");
        this.loading = new openerp.base.Loading(this.session, "oe_loading");
        this.crashmanager =  new openerp.base.CrashManager(this.session);

        // Do you autorize this ?
        openerp.base.Controller.prototype.notification = new openerp.base.Notification(this.session, "oe_notification");

        this.header = new openerp.base.Header(this.session, "oe_header");
        this.login = new openerp.base.Login(this.session, "oe_login");

        this.session.on_session_invalid.add(this.login.do_ask_login);
        this.session.on_session_valid.add_last(this.header.do_update);
        this.session.on_session_valid.add_last(this.on_logged);

        this.menu = new openerp.base.Menu(this.session, "oe_menu", "oe_secondary_menu");
        this.menu.on_action.add(this.on_menu_action);
    },
    start: function() {
        this.session.start();
        this.header.start();
        this.login.start();
        this.menu.start();
        this.notification['default']("OpenERP Client", "The openerp client has been initialized.");
    },
    on_logged: function() {
        this.action =  new openerp.base.ActionManager(this.session, "oe_app");
        this.action.start();
    },
    on_menu_action: function(action) {
        this.action.do_action(action);
    },
    do_about: function() {
    }
});

openerp.base.webclient = function(element_id) {
    // TODO Helper to start webclient rename it openerp.base.webclient
    var client = new openerp.base.WebClient(element_id);
    client.start();
    return client;
};
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
