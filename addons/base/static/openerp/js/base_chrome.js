/*---------------------------------------------------------
 * OpenERP base library
 *---------------------------------------------------------*/

openerp.base$chrome = function(openerp) {

openerp.base.callback = function(obj, method) {
    // openerp.base.callback( obj, methods, [arg1, arg2, ... ] )
    //
    // The callback object holds a chain that can be altered:
    // callback.add( handler , [arg1, arg2, ... ] )
    // callback.add( {
    //     callback: function
    //     self: object or null
    //     args: array
    //     position: "first" or "last"
    //     unique: boolean
    // })
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

openerp.base.BasicController = Class.extend({
    // TODO: init and start semantics are not clearly defined yet
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
    start: function() {
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
        console.log(arguments);
    },
    on_ready: function() {
    }
});

openerp.base.Console =  openerp.base.BasicController.extend({
    init: function(element_id, server, port) {
        this._super(element_id);
    },
    on_log: function() {
        // TODO this should move to Console and be active only in debug
        // TODO $element should be for error not log
        var self = this;
        this._super.apply(this,arguments);
        $.each(arguments, function(i,v) {
            if(self.$element) {
                v = v==null ? "null" : v;
                $('<pre></pre>').text(v.toString()).appendTo(self.$element);
            }
        });
    }
});

openerp.base.Database = openerp.base.BasicController.extend({
// Non Session Controller to manage databases
});

openerp.base.Session = openerp.base.BasicController.extend({
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
    rpc: function(url, params, success_callback, error_callback) {
        // Construct a JSON-RPC2 request, method is currently unused
        params.session_id = this.session_id;
        params.context = typeof(params.context) != "undefined" ? params.context  : this.context;

        // Use a default error handler unless defined
        error_callback = typeof(error_callback) != "undefined" ? error_callback : this.on_rpc_error;

        // Call using the rpc_mode
        this.rpc_ajax(url, {
            jsonrpc: "2.0",
            method: "call",
            params: params,
            id:null
        }, success_callback, error_callback);
    },
    rpc_ajax: function(url, payload, success_callback, error_callback) {
        var self = this;
        this.on_rpc_request();
        $.ajax({
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
        });
    },
    on_rpc_request: function() {
    },
    on_rpc_response: function() {
    },
    on_rpc_error: function(error) {
        // TODO this should use the $element with focus and button is displaying OPW etc...
        this.on_log(error.message, error.data);
    },
    on_session_invalid: function(contination) {
    },
    session_valid: function() {
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
            self.session_check_modules();
            if (success_callback)
                success_callback();
        });
    },
    session_check_modules: function() {
        if(!openerp._modules_loaded)
            this.session_load_modules();
    },
    session_load_modules: function() {
        var self = this;
        this.rpc('/base/session/modules', {}, function(result) {
            self.module_list = result['modules'];
            self.rpc('/base/session/jslist', {"mods": self.module_list.join(',')}, self.debug ? self.do_session_load_modules_debug : self.do_session_load_modules_prod);
            openerp._modules_loaded = true;
        });
    },
    do_session_load_modules_debug: function(result) {
        var self = this;
        var files = result.files;
        // Insert addons javascript in head
        for(var i=0; i<files.length; i++) {
            var s = document.createElement("script");
            s.src = files[i];
            s.type = "text/javascript";
            document.getElementsByTagName("head")[0].appendChild(s);
        }
        // at this point the js should be loaded or not ?
        setTimeout(self.on_session_modules_loaded,100);
    },
    do_session_load_modules_prod: function() {
        // load merged ones
        // /base/session/css?mod=mod1,mod2,mod3
        // /base/session/js?mod=mod1,mod2,mod3
        // use $.getScript(‘your_3rd_party-script.js’); ? i want to keep lineno !
    },
    on_session_modules_loaded: function() {
        var self = this;
        for(var j=0; j<self.module_list.length; j++) {
            var mod = self.module_list[j];
            self.log("init module "+mod);
            if(self.module_loaded[mod])
                continue;
            openerp[mod] = {};
            // init module mod
            openerp._openerp[mod](openerp);
            self.module_loaded[mod] = true;
        }
    },
    session_logout: function() {
        this.uid = false;
    }
});

openerp.base.Controller = openerp.base.BasicController.extend({
    init: function(session, element_id) {
        this._super(element_id);
        this.session = session;
    },
    on_log: function() {
        if(this.session)
            this.session.log.apply(this.session,arguments);
    },
    rpc: function(url, data, success, error) {
        // TODO: support additional arguments ?
        this.session.rpc(url, data, success, error);
    }
});

openerp.base.Loading =  openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
        this.count = 0;
    },
    start: function() {
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

openerp.base.Header =  openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
    },
    start: function() {
        this.$element.html(QWeb.render("Header", {}));
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
            .addClass("login_valid")
            .removeClass("login_invalid")
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
            if(self.session.session_valid()) {
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

openerp.base.Menu =  openerp.base.Controller.extend({
    init: function(session, element_id, model) {
        this._super(session, element_id);
        this.menu = false;
    },
    start: function() {
        this.rpc("/base/menu/load", {}, this.on_loaded);
    },
    on_loaded: function(data) {
        this.data = data;
        var $e = this.$element;
        $e.html(QWeb.render("Menu.root", this.data));
        $("ul.sf-menu").superfish({
            speed: 'fast'
        });
        $e.find("a").click(this.on_menu_click);
        this.on_ready();
    },
    on_menu_click: function(ev) {
        var menu_id = Number(ev.target.id.split("_").pop());
        this.rpc("/base/menu/action", {"menu_id":menu_id}, this.on_menu_action_loaded);
        return false;
    },
    on_menu_action_loaded: function(data) {
        var self = this;
        if(data.action.length) {
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

        QWeb.add_template("base.xml");
        this.$element.html(QWeb.render("Interface", {}));

        this.session = new openerp.base.Session("oe_errors");

        this.loading = new openerp.base.Loading(this.session, "oe_loading");

        this.login = new openerp.base.Login(this.session, "oe_login");

        this.header = new openerp.base.Header(this.session, "oe_header");

        this.login.on_login_valid.add(function() {
            self.$element.find(".on_logged").show();
        });

        // TODO MOVE ALL OF THAT IN on_logged
        // after pooler update of modules
        // Cool no ?
        this.session.on_session_invalid.add(this.login.do_ask_login);

        this.menu = new openerp.base.Menu(this.session, "oe_menu");
        this.menu.on_ready.add(this.on_menu_ready);
        this.menu.on_action.add(this.on_menu_action);

        this.action =  new openerp.base.Action(this.session, "oe_main");

    },
    start: function() {
        this.loading.start();
        this.login.start();
        this.header.start();
        this.menu.start();
        this.action.start();
    },
    on_menu_ready: function() {
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
