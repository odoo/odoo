
openerp.web_mobile = function(openerp) {
    
openerp.web_mobile = {};
    
openerp.web_mobile.MobileWebClient = openerp.base.Controller.extend({
    init: function(element_id) {
        var self = this;
        this._super(null, element_id);
        QWeb.add_template("xml/mobile.xml");
        var params = {};

        this.$element.html(QWeb.render("WebClient", {}));
        this.session = new openerp.base.Session("oe_errors");
        this.crashmanager =  new openerp.base.CrashManager(this.session);
        this.login = new openerp.web_mobile.Login(this.session, "oe_app");

        this.session.on_session_invalid.add(this.login.do_ask_login);
        this.session.on_session_valid.add_last(this.on_logged);
       
    },
    start: function() {
        this.session.start();
        this.login.start();

    },
    on_logged: function() {
    
    	//this.$element.html(QWeb.render("ListView", {}));
        /*this.action_manager =  new openerp.base.ActionManager(this.session, "oe_app");*/
        //this.action_manager.start();
        
    },
   /* session_login: function(db, login, password, success_callback) {
        var self = this;
        this.db = db;
        this.login = login;
        this.password = password;
        var params = { db: this.db, login: this.login, password: this.password };
        this.rpc("/web_mobile/mobile/login", params, function(result) {
            self.session_id = result.session_id;
            self.uid = result.uid;
            self.session_save();
            self.on_session_valid();
            if (success_callback)
                success_callback();
        });
    },*/
    on_menu_action: function(action) {
        //this.action_manager.do_action(action);
    },
    do_about: function() {
    }
});

openerp.web_mobile.mobilewebclient = function(element_id) {
    // TODO Helper to start webclient rename it openerp.base.webclient
    var client = new openerp.web_mobile.MobileWebClient(element_id);
    client.start();
    return client;
};

openerp.base.Header =  openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
    },
    start: function() {
        this.$element.html(QWeb.render("Header", this));
        this.$element.find("a").click(this.on_clicked);
    },
    on_clicked: function(ev) {
        $opt = $(ev.currentTarget);
        current_id = $opt.attr('id');
        if (current_id == 'home') {
            this.homepage = new openerp.web_mobile.Login(this.session, "oe_app");
            this.homepage.on_login_valid();
        }
    }
    
});

openerp.base.Shortcuts =  openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
    },
    start: function() {
        var self = this;
        this.rpc('/web_mobile/mobile/sc_list',{} ,function(res){
            self.$element.html(QWeb.render("Shortcuts", {'sc' : res}))
            self.$element.find("a").click(self.on_clicked);
        })
    },
    on_clicked: function(ev) {
        $shortcut = $(ev.currentTarget);
        id = $shortcut.data('menu');
        res_id = $shortcut.data('res');
        jQuery("#oe_header").find("h1").html($shortcut.data('name'));
        this.listview = new openerp.base.ListView(this.session, "oe_app", res_id);
        this.listview.start();
    }
});

openerp.base.ListView = openerp.base.Controller.extend({
    init: function(session, element_id, list_id) {
        this._super(session, element_id);
        this.list_id = list_id;
    },
    start: function() {
        this.rpc('/web_mobile/menu/action', {'menu_id': this.list_id},
                    this.on_menu_action_loaded);
    },
    on_menu_action_loaded: function(data) {
        var self = this;
        if (data.action.length) {
            var action = data.action[0][2];
            self.on_action(action);
        }
    },
    on_action: function(action) {
        var self = this;
        var view_id = action.views[0][0];
        var model = action.res_model;
        var context = action.context;
        var domain = action.domain;
        self.rpc('/web_mobile/listview/fill', {
            'model': model,
            'id': view_id,
            'context': context,
            'domain': domain
            },function(result){
                this.listview = new openerp.base.ListView(this.session, "oe_app");
                self.$element.html(QWeb.render("ListView", {'list' : result}));
            });
    }
 });

openerp.base.Secondary =  openerp.base.Controller.extend({
    init: function(session, element_id, secondary_menu_id) {
        this._super(session, element_id);
        this.data = secondary_menu_id;
    },
    start: function(ev, id) {
        var v = { menu : this.data };
        this.$element.html(QWeb.render("Menu.secondary", v));
        this.$element.add(this.$secondary_menu).find("a").click(this.on_menu_click);
    },
    on_menu_click: function(ev, id) {
        $menu = $(ev.currentTarget);
        id = $menu.data('menu');
        for (var i = 0; i < this.data.children.length; i++) {
            if (this.data.children[i].id == id) {
                this.children = this.data.children[i];
            }
        }
        jQuery("#oe_header").find("h1").html($menu.data('name'));

        var child_len = this.children.children.length;
        if (child_len > 0) {
            this.$element
                .removeClass("secondary_menu")
                .addClass("content_menu");
                //.hide();
            this.secondary = new openerp.base.Secondary(this.session, "oe_app", this.children);
            this.secondary.start();
        }
        else {
            if (id) {
            this.listview = new openerp.base.ListView(this.session, "oe_app", id);
            this.listview.start();
            }
        }
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
        this.rpc("/web_mobile/menu/load", {}, this.on_loaded);
    },
    on_loaded: function(data) {
        this.data = data;
        this.$element.html(QWeb.render("Menu", this.data));
        this.$element.add(this.$secondary_menu).find("a").click(this.on_menu_click);
    },
    on_menu_click: function(ev, id) {
        $menu = $(ev.currentTarget);
        id = $menu.data('menu');
        for (var i = 0; i < this.data.data.children.length; i++) {
            if (this.data.data.children[i].id == id) {
                this.children = this.data.data.children[i];
            }
        }
        jQuery("#oe_header").find("h1").html($menu.data('name'));
        this.$element
            .removeClass("login_valid")
            .addClass("secondary_menu");
            //.hide();
        this.secondary = new openerp.base.Secondary(this.session, "oe_app", this.children);
        this.secondary.start();
    }
});

openerp.base.Options =  openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
    },
    start: function() {
        var self = this;
        this.$element.html(QWeb.render("Options", this));
        self.$element.find("a").click(self.on_clicked);
    },
    on_clicked: function(ev) {
        $opt = $(ev.currentTarget);
        current_id = $opt.attr('id');
        if (current_id == 'logout') {
            this.rpc('/web_mobile/mobile/logout', {});
            this.login = new openerp.web_mobile.Login(this.session, "oe_app");
            this.login.start();
        }
    }
});
openerp.web_mobile.Login =  openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
    },
    start: function() {
        var self = this;

        jQuery("#oe_header").children().remove();
        this.rpc('/web_mobile/mobile/db_list',{} ,function(res){
            self.$element.html(QWeb.render("Login", {'db' : res}));
            self.$element.find('#database').click(self.on_select);
            self.$element.find("a").click(self.on_clicked);
        })
    },
    on_select: function(ev) {
        var db = this.$element.find("#database option:selected").val();
        jQuery("#db_text").html(db);
    },
    on_clicked: function(ev) {
        $opt = $(ev.currentTarget);
        current_id = $opt.attr('id');
        if (current_id = "login") {
            ev.preventDefault();
            var self = this;
            var $e = this.$element;
            var db = $e.find("div select[name=database]").val();
            var login = $e.find("div input[name=login]").val();
            var password = $e.find("div input[name=password]").val();
            //$e.hide();
            // Should hide then call callback
            this.session.session_login(db, login, password, function() {
                if(self.session.session_is_valid()) {
                    self.on_login_valid();
                } else {
                    self.on_login_invalid();
                }
            });
        }
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
            .addClass("login_valid");
            //.hide();
        this.$element.html(QWeb.render("HomePage", {}));
        this.header = new openerp.base.Header(this.session, "oe_header");
        this.shortcuts = new openerp.base.Shortcuts(this.session, "oe_shortcuts");
        this.menu = new openerp.base.Menu(this.session, "oe_menu", "oe_secondary_menu");
        this.options = new openerp.base.Options(this.session, "oe_options");
        this.header.start();
        this.shortcuts.start();
        this.menu.start();
        this.options.start();
        jQuery("#oe_header").find("h1").html('Home');

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
    
};
