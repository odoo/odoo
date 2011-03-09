/*---------------------------------------------------------
 * John Resig Class, to be moved to openerp.base.Class
 *---------------------------------------------------------*/

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
      if ( !initializing && this.init )
        this.init.apply(this, arguments);
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

//---------------------------------------------------------
// OpenERP initalisation and black magic about the pool
//---------------------------------------------------------

(function(){

if(this.openerp)
    return;

var openerp = this.openerp = function() {
    // create a new pool instance
    var o = {};

    // links to the global openerp
    o._openerp = openerp;

    // Only base will be loaded, the rest will be by loaded by
    // openerp.base.Connection on the first connection
    o._modules_loaded = false

    // this unique id will be replaced by hostname_databasename by
    // openerp.base.Connection on the first connection
    o._unique_id = "unique_id_cause_db_name_is_not_yet_known"
    openerp.pool[o._unique_id] = o;

    o.screen = openerp.screen;
    o.pool = openerp.pool;
    o.base = {};
    openerp.base(o);

    return o;
}

// element_ids registry linked to all controllers on the page
// TODO rename to elements, or keep gtk naming?
openerp.screen = {};

// per database openerp like namespace
// openerp.<module> for module will to
// openerp.pool.<dbname>.<module> using a closure
// TODO rename it openerp.connections
openerp.pool = {};

})();

/*---------------------------------------------------------
 * OpenERP base library
 *---------------------------------------------------------*/

openerp.base = function(openerp) {

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
    var args = Array.prototype.slice.call(arguments);
    var callback = function() {
        var args2 = Array.prototype.slice.call(arguments);
        var r;
        for(var i = 0; i < callback.callback_chain.length; i++)  {
            var c = callback.callback_chain[i];
            if(c.unique) {
                // al: obscure but shortening C-style hack, sorry
                callback.callback_chain.pop(i--);
            }
            r = c.callback.apply(c.self, c.args.concat(args2));
            // TODO special value to stop the chain
            // openerp.base.callback_stop
        }
        return r;
    };
    callback.callback_chain = [];
    callback.add = function(f) {
        var args2 = Array.prototype.slice.call(arguments);
        if(typeof(f) == 'function') {
            f = { callback: f, args: args2.slice(1) };
        }
        f.self = f.self || null;
        f.args = f.args || [];
        f.unique = f.unique || false;
        if(f.position == 'last') {
            callback.callback_chain.push(f);
        } else {
            callback.callback_chain.unshift(f);
        }
        return callback;
    };
    callback.add_first = function(f) {
        callback.add.apply(null,arguments);
    };
    callback.add_last = function(f) {
        var args2 = Array.prototype.slice.call(arguments);
        callback.add({callback: f, args: args2.slice(1), position: "last"});
    };
    callback.add({ callback: method, self:obj, args:args.slice(2) });
    return callback;
}

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
    },
});

openerp.base.Console =  openerp.base.BasicController.extend({
});

openerp.base.Database = openerp.base.BasicController.extend({
// Non Session Controller to manage databases
})

openerp.base.Connection = openerp.base.BasicController.extend({
// This store the webclient servername port and the database
// this correpond to one pool entry
// TODO on first connection:
// rename the uniquename in openerp.connnections
// do the magic of loading all the modules by loading missing module and their
// javascript using a dom nodes with urls:
// /base/connection/css?mod=mod1,mod2,mod3
// /base/connection/js?mod=mod1,mod2,mod3
// then init them
// for i in installed_modules:
//     call openerp._openerp.<i>(openerp)
})

openerp.base.Session = openerp.base.BasicController.extend({
    init: function(element_id, server, port) {
        this._super(element_id);
        this.rpc_mode = (server == undefined) ? "ajax" : "jsonp";
        this.server = (server == undefined) ? location.hostname : server;
        this.port = (port == undefined) ? location.port : port;
        this.login = "";
        this.password = "";
        this.uid = false;
        this.session_id = false;
        this.context = {};
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
    },
    rpc: function(url, params, success_callback, error_callback) {
        // TODO keep a this.ajax_count counter to display LOADING
        var self = this;

        this.on_rpc_request();

        // Construct a JSON-RPC2 request, method is currently unsed
        params.session_id = this.session_id;
        params.context = typeof(params.context) != "undefined" ? params.context  : this.context;
        var request = { jsonrpc: "2.0", method: "call", params: params, "id":null };

        // This is a violation of the JSON-RPC2 over HTTP protocol
        // specification but i dont know how to parse the raw POST content from
        // cherrypy so i use a POST form with one variable named request
        var post = { request: JSON.stringify(request) };

        // Use a default error handler unless defined
        error_callback = typeof(error_callback) != "undefined" ? error_callback : this.on_error;

        $.ajax({
            type: "POST",
            //async: false,
            url: url,
            dataType: 'json',
            data: post,
            success: function(response, textStatus, jqXHR) {
                self.on_rpc_response();
                if (response.error) {
                    if (response.error.data.type == "session_invalid") {
                        self.uid = false;
                        self.on_session_invalid(function() {
                            self.rpc(url, params, success_callback, error_callback);
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
                    code: 1,
                    message: "XmlHttpRequestError " + errorThrown,
                    data: {
                        type: "xhr"+textStatus,
                        debug: jqXHR.responseText,
                        objects: [ jqXHR, errorThrown ]
                    }
                };
                error_callback(error);
            }
        });
    },
    on_rpc_request: function() {
    },
    on_rpc_response: function() {
    },
    on_error: function(error) {
        // TODO this should use the $element with focus and buttonsi displaying OPW etc...
        this.on_log(error, error.message, error.data.type, error.data.debug);
    },
    on_session_invalid: function(contination) {
    },
    session_valid: function() {
        return this.uid;
    },
    session_login: function(db, login, password, sucess_callback) {
        var self = this;
        this.db = db;
        this.login = login;
        this.password = password;
        var params = { db: this.db, login: this.login, password: this.password }
        this.rpc("/base/session/login", params, function(result) {
            self.session_id = result.session_id;
            self.uid = result.uid;
            if (sucess_callback) sucess_callback();
        });
    },
    session_logout: function() {
        this.uid = false;
    },
})

openerp.base.Controller = openerp.base.BasicController.extend({
    init: function(session, element_id) {
        this._super(element_id);
        this.session = session
    },
    on_log: function() {
        if(this.session)
            this.session.log.apply(this.session,arguments);
    },
    rpc: function(url, data, success, error) {
        // TODO: support additional arguments ?
        this.session.rpc(url, data, success, error);
    },
})

openerp.base.Loading =  openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
        this.count = 0;
    },
    start: function() {
        var self =this;
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
    },
});

openerp.base.Login =  openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
    },
    start: function() {
        this.$element.html(QWeb.render("Login", {}));
        this.on_login_invalid();
        this.$element.find("form").submit(this.on_submit);
    },
    on_login_invalid: function() {
        var $e = this.$element;
        $e.removeClass("login_valid");
        $e.addClass("login_invalid");
        $e.show();
    },
    on_login_valid: function() {
        var $e = this.$element;
        $e.removeClass("oe_login_invalid");
        $e.addClass("login_valid");
        $e.hide();
    },
    on_submit: function(ev) {
        var self = this;
        var $e = this.$element;
        var login = $e.find("form input[name=login]").val();
        var password = $e.find("form input[name=password]").val();
        //$e.hide();
        // Should hide then call calllback
        this.session.session_login("", login, password, function() {
            if(self.session.session_valid()) {
                self.on_login_valid();
            } else {
                self.on_login_invalid();
            }
        });
        return false;
    },
    do_ask_login: function(continuation) {
        var self = this;
        this.on_login_invalid();
        this.on_submit.add({
            position: "last",
            unique: true,
            callback: function() {
                if(continuation) continuation();
                return false;
            }});
    },
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
            speed: 'fast',
        });
        $e.find("a").click(this.on_menu_click);
        this.on_ready();
    },
    on_menu_click: function(ev) {
        var self = this;
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
    },
});

openerp.base.DataSet =  openerp.base.Controller.extend({
    init: function(session, element_id, model) {
        this._super(session, element_id);
        this.model = model;
        this.model_fields = null;
        this.fields = [];
        // SHOULD USE THE ONE FROM FIELDS VIEW GET BECAUSE OF SELECTION
        this.domain = [];
        this.context = {};
        this.order = "";
        this.count;
        this.ids = [];
        this.values = {};
/*
    group_by
        rows record
            fields of row1 field fieldname
                { type: value: text: text_format: text_completions type_*: a
*/
    },
    start: function() {
        this.rpc("/base/dataset/fields", {"model":this.model}, this.on_fields);
    },
    on_fields: function(result) {
        this.model_fields = result.fields;
        this.on_ready();
    },
    do_load: function(offset, limit) {
        this.rpc("/base/dataset/load", {model: this.model, fields: this.fields }, this.on_loaded);
    },
    on_loaded: function(data) {
        this.ids = data.ids
        this.values = data.values
    },
    on_reloaded: function(ids) {
    },
});

openerp.base.DataRecord =  openerp.base.Controller.extend({
    init: function(session, element_id, model, id) {
        this._super(session, element_id);
        this.model = model;
        this.id = id;
    },
    start: function() {
    },
    on_ready: function() {
    },
    on_change: function() {
    },
    on_reload: function() {
    },
});

openerp.base.FormView =  openerp.base.Controller.extend({
    init: function(session, element_id, dataset, view_id) {
        this._super(session, element_id);
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
    },
    start: function() {
        //this.log('Starting FormView '+this.model+this.view_id)
        this.rpc("/base/formview/load", {"model": this.model, "view_id":this.view_id}, this.on_loaded);
    },
    on_loaded: function(data) {
        this.fields_view = data.fields_view;
        //this.log(this.fields_view);
        this.$element.html(QWeb.render("FormView", {"fields_view": this.fields_view}));
    },
    on_button: function() {
    },
    on_write: function() {
    },
});

openerp.base.ListView = openerp.base.Controller.extend({
    init: function(session, element_id, dataset, view_id) {
        this._super(session, element_id);
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.name = "";

        this.cols = [];

        this.$table = null;
        this.colnames = [];
        this.colmodel = [];

        this.event_loading = false; // TODO in the future prevent abusive click by masking
    },
    start: function() {
        //this.log('Starting ListView '+this.model+this.view_id)
        this.rpc("/base/listview/load", {"model": this.model, "view_id":this.view_id}, this.on_loaded);
    },
    on_loaded: function(data) {
        var self = this;
        this.fields_view = data.fields_view;
        //this.log(this.fields_view);
        this.name = "" + this.fields_view.arch.attrs.string;
        this.$element.html(QWeb.render("ListView", {"fields_view": this.fields_view}));
        this.$table = this.$element.find("table");
        this.cols = [];
        this.colnames = [];
        this.colmodel = [];
        // TODO uss a object for each col, fill it with view and fallback to dataset.model_field
        var tree = this.fields_view.arch.children;
        for(var i = 0; i < tree.length; i++)  {
            var col = tree[i];
            if(col.tag == "field") {
                this.cols.push(col.attrs.name);
                this.colnames.push(col.attrs.name);
                this.colmodel.push({ name: col.attrs.name, index: col.attrs.name });
            }
        }
        //this.log(this.cols);
        this.dataset.fields = this.cols;
        this.dataset.on_loaded.add_last(this.do_fill_table);
    },
    do_fill_table: function() {
        //this.log("do_fill_table");
        
        var self = this;
        //this.log(this.dataset.data);
        var rows = [];
        var ids = this.dataset.ids;
        for(var i = 0; i < ids.length; i++)  {
            // TODO very strange is sometimes non existing ? even as admin ? example ir.ui.menu
            var row = this.dataset.values[ids[i]];
            if(row)
                rows.push(row);
//            else
//              debugger;
        }
        //this.log(rows);
        this.$table.jqGrid({
            data: rows,
            datatype: "local",
            height: "100%",
            rowNum: 100,
            //rowList: [10,20,30],
            colNames: this.colnames,
            colModel: this.colmodel,
            //pager: "#plist47",
            viewrecords: true,
            caption: this.name
        }).setGridWidth(this.$element.width());
        $(window).bind('resize', function() { self.$table.setGridWidth(self.$element.width()); }).trigger('resize');
    },
});


openerp.base.SearchViewInput = openerp.base.Controller.extend({
// TODO not sure should we create a controler for every input ?

// of we just keep a simple dict for each input in
// openerp.base.SearchView#input_ids
// and use if when we get an event depending on the type
// i think it's less bloated to avoid useless controllers

// but i think for many2one a controller would be nice
// so simple dict for simple inputs
// an controller for many2one ?

});


openerp.base.SearchView = openerp.base.Controller.extend({
    init: function(session, element_id, dataset, view_id) {
        this._super(session, element_id);
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.input_index = 0;
        this.input_ids = {};
        this.domain = [];
    },
    start: function() {
        //this.log('Starting SearchView '+this.model+this.view_id)
        this.rpc("/base/searchview/load", {"model": this.model, "view_id":this.view_id}, this.on_loaded);
    },
    on_loaded: function(data) {
        this.fields_view = data.fields_view;
        this.log(this.fields_view);
        this.input_ids = {};
        this.$element.html(QWeb.render("SearchView", {"fields_view": this.fields_view}));
        this.$element.find("#search").bind('click',this.on_search);
        // TODO bind click event on all button
        // TODO we dont do many2one yet, but in the future bind a many2one controller on them
        this.log(this.$element.find("#search"));
    },
    register_input: function(node) {
        // self should be passed in the qweb dict to do:
        // <input t-add-id="self.register_input(node)"/>

        // generate id
        var id = this.element_id + "_" + this.input_index++;
        // TODO construct a nice object
        var input = {
            node: node,
            type: "filter",
            domain: "",
            context: "",
            disabled: false,
        };
        // save it in our registry
        this.input_ids[id] = input;

        return id;
    },
    on_click: function() {
        // event catched on a button
        // flip the disabled flag
        // adjust the css class
    },
    on_search: function() {
        this.log("on_search");
        // collect all non disabled domains definitions, AND them
        // evaluate as python expression
        // save the result in this.domain
    },
    on_clear: function() {
    },
});

openerp.base.Action =  openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
        this.action = null;
        this.dataset = null;
        this.searchview_id = false;
        this.searchview = null;
        this.listview_id = false;
        this.listview = null;
        this.formview_id = false;
        this.formview = null;
    },
    start: function() {
        this.$element.html(QWeb.render("Action", {"prefix":this.element_id}));
        this.$element.find("#mode_list").bind('click',this.on_mode_list);
        this.$element.find("#mode_form").bind('click',this.on_mode_form);
        this.on_mode_list();
    },
    on_mode_list: function() {
        $("#oe_action_form").hide();
        $("#oe_action_search").show();
        $("#oe_action_list").show();
    },
    on_mode_form: function() {
        $("#oe_action_form").show();
        $("#oe_action_search").hide();
        $("#oe_action_list").hide();
    },
    do_action: function(action) {
        // instanciate the right controllers by understanding the action
        this.action = action;
        this.log(action);
//        debugger;
        //this.log(action);
        if(action.type == "ir.actions.act_window") {
            this.do_action_window(action);
        }
    },
    do_action_window: function(action) {
        this.formview_id = false;
        this.dataset = new openerp.base.DataSet(this.session, "oe_action_dataset", action.res_model);
        this.dataset.start();

        // Locate first tree view
        this.listview_id = false;
        for(var i = 0; i < action.views.length; i++)  {
            if(action.views[i][1] == "tree") {
                this.listview_id = action.views[i][0];
                break;
            }
        }
        this.listview = new openerp.base.ListView(this.session, "oe_action_list", this.dataset, this.listview_id);
        this.listview.start();

        // Locate first form view
        this.listview_id = false;
        for(var i = 0; i < action.views.length; i++)  {
            if(action.views[i][1] == "form") {
                this.formview_id = action.views[i][0];
                break;
            }
        }
        this.formview = new openerp.base.FormView(this.session, "oe_action_form", this.dataset, this.formview_id);
        this.formview.start();

        // Take the only possible search view. Is that consistent ?
        this.searchview_id = false;
        if(this.listview && action.search_view_id) {
            this.searchview_id = action.search_view_id[0];
        }
        this.searchview = new openerp.base.SearchView(this.session, "oe_action_search", this.dataset, this.searchview_id);
        this.searchview.start();

        // Connect the the dataset load event with the search button of search view
        // THIS IS COOL
        this.searchview.on_search.add_last(this.dataset.do_load);
    },
});

openerp.base.WebClient = openerp.base.Controller.extend({
    init: function(element_id) {
        this._super(null, element_id);

        QWeb.add_template("base.xml");
        this.$element.html(QWeb.render("Interface", {}));

        this.session = new openerp.base.Session("oe_errors");

        this.loading = new openerp.base.Loading(this.session, "oe_loading");

        this.login = new openerp.base.Login(this.session, "oe_login");

        this.header = new openerp.base.Header(this.session, "oe_header");

        // TODO MOVE ALL OF THAT IN on_loggued
        // after pooler udpate of modules
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
});

openerp.base.webclient = function(element_id) {
    // TODO Helper to start webclient rename it openerp.base.webclient
    var client = new openerp.base.WebClient(element_id);
    client.start();
    return client;
}

};

// DEBUG_RPC:rpc.request:('execute', 'addons-dsh-l10n_us', 1, '*', ('ir.filters', 'get_filters', u'res.partner'))
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
