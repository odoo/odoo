/*---------------------------------------------------------
 * OpenERP Web Mobile chrome
 *---------------------------------------------------------*/

openerp.web_mobile.chrome_mobile = function(instance) {

instance.web_mobile.mobilewebclient = function(element_id) {
    // TODO Helper to start mobile webclient rename it instance.web.webclient
    var client = new instance.web_mobile.MobileWebClient(element_id);
    client.start();
    return client;
};

instance.web_mobile.MobileWebClient = instance.web.OldWidget.extend({

    template: "WebClient",

    init: function(element_id) {
        this._super(null, element_id);
        this.crashmanager =  new instance.web.CrashManager(this);
        this.login = new instance.web_mobile.Login(this, "oe_login");
    },
    start: function() {
        this._super.apply(this, arguments);
        var self = this;
        this.session.bind_session().then(function() {
            instance.web.qweb.add_template("xml/web_mobile.xml");
            self.$element.html(self.render());
            self.login.start();
        });
    }
});

instance.web_mobile.Login =  instance.web.OldWidget.extend({

    template: "Login",

    start: function() {
        this.has_local_storage = typeof(localStorage) != 'undefined';
        this.remember_creditentials = true;
        this.selected_login = null;
        this.selected_password = null;
        if (this.has_local_storage && this.remember_creditentials) {
            this.selected_login = localStorage.getItem('last_login_login_success');
            this.selected_password = localStorage.getItem('last_password_login_success');
        }
        var self = this;
        jQuery("#oe_header").children().remove();
        this.rpc("/web/database/get_list", {}, function(result) {
            self.db_list = result.db_list;
            this.setElement($('#'+self.element_id).html(self.render(self)));
            if(self.session.db!=""){
                self.$element.find("#database").val(self.session.db);
            }
            self.$element.find("#login_btn").click(self.on_login);
            $.mobile.initializePage();
        });
        this.$element
            .removeClass("login_invalid");
    },
    on_login: function(ev) {
        ev.preventDefault();
        var self = this;
        var $e = this.$element;
        var db = $e.find("div select[name=database]").val();
        var login = $e.find("div input[name=login]").val();
        var password = $e.find("div input[name=password]").val();
        //$e.hide();
        // Should hide then call callback
        this.session.session_authenticate(db, login, password).then(function() {
            if(self.session.session_is_valid()) {
                if (self.has_local_storage) {
                    if(self.remember_creditentials) {
                        localStorage.setItem('last_db_login_success', db);
                        localStorage.setItem('last_login_login_success', login);
                        localStorage.setItem('last_password_login_success', password);
                    } else {
                        localStorage.setItem('last_db_login_success', '');
                        localStorage.setItem('last_login_login_success', '');
                        localStorage.setItem('last_password_login_success', '');
                    }
                }
                self.on_login_valid();
            } 
        });
        this.session.on_session_invalid.add({
            callback: function () {
                self.on_login_invalid();
            },
            unique: true
        });
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
        if(!$('#oe_menu').html().length){
            this.menu = new instance.web_mobile.Menu(this, "oe_menu", "oe_secondary_menu");
            this.menu.start();
        }else{
            $.mobile.changePage("#oe_menu", "slide", false, true);
        }
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

instance.web_mobile.Header =  instance.web.OldWidget.extend({

    template: "Header",

    init: function(session, element_id) {
        this._super(session, element_id);
    },
    start: function() {
        this.$element.html(this.render(this));
    }
});

instance.web_mobile.Footer =  instance.web.OldWidget.extend({

    template: "Footer",

    init: function(session, element_id) {
        this._super(session, element_id);
    },
    start: function() {
        this.$element.html(this.render(this));
    }
});

instance.web_mobile.Shortcuts =  instance.web.OldWidget.extend({

    template: "Shortcuts",

    init: function(session, element_id) {
        this._super(session, element_id);
    },
    start: function() {
        var self = this;
        this.rpc('/web/session/sc_list',{} ,function(res){
            self.$element.html(self.render({'sc': res}));
            self.$element.find("[data-role=header]").find('h1').html('Favourite');
            self.$element.find("[data-role=header]").find('#home').click(function(){
                $.mobile.changePage("#oe_menu", "slide", false, true);
            });
            self.$element.find('#content').find("a").click(self.on_clicked);
            $.mobile.changePage("#oe_shortcuts", "slide", false, true);
        });
    },
    on_clicked: function(ev) {
        var self = this;
        ev.preventDefault();
        ev.stopPropagation();
        $shortcut = $(ev.currentTarget);
        id = $shortcut.data('menu');
        res_id = $shortcut.data('res');
        if(!$('[id^="oe_list_'+res_id+'"]').html()){
            $('<div id="oe_list_'+res_id+'" data-role="page" data-url="oe_list_'+res_id+'"> </div>').appendTo('#moe');
            this.listview = new instance.web_mobile.ListView(self, "oe_list_"+res_id, res_id);
            this.listview.start();
        }else{
            $.mobile.changePage('#oe_list_'+res_id, "slide", false, true);
        }
        ev.preventDefault();
        ev.stopPropagation();
        jQuery("#oe_header").find("h1").html($shortcut.data('name'));
    }
});

instance.web_mobile.Menu =  instance.web.OldWidget.extend({

    template: "Menu",

    init: function(session, element_id, secondary_menu_id) {
        this._super(session, element_id);
        this.secondary_menu_id = secondary_menu_id;
        this.$secondary_menu = $("#" + secondary_menu_id);
        this.menu = false;
    },
    start: function() {
        this._super.apply(this, arguments);
        this.rpc("/web/menu/load", {}, this.on_loaded);
    },
    on_loaded: function(data) {
        var self = this;
        this.data = data;
        this.header = new instance.web_mobile.Header(this, "oe_header");
        this.header.start();
        this.footer = new instance.web_mobile.Footer(this, "oe_footer");
        this.footer.start();
        this.$element.html(this.render(this.data));
        this.$element.find("[data-role=header]").find('h1').html('Applications');
        this.$element.find("[data-role=header]").find('#home').hide();
        this.$element.find("[data-role=footer]").find('#shrotcuts').click(function(){
            if(!$('#oe_shortcuts').html().length){
                this.shortcuts = new instance.web_mobile.Shortcuts(self, "oe_shortcuts");
                this.shortcuts.start();
            }else{
                $.mobile.changePage($("#oe_shortcuts"), "slide", false, true);
            }
        });
        this.$element.find("[data-role=footer]").find('#preference').click(function(){
            if(!$('#oe_options').html().length){
                this.options = new instance.web_mobile.Options(self, "oe_options");
                this.options.start();
            }else{
                $.mobile.changePage("#oe_options", "slide", false, true);
            }
        });
        this.$element.add(this.$secondary_menu).find("#content").find('a').click(this.on_menu_click);
        $.mobile.changePage("#oe_menu", "slide", false, true);
    },
    on_menu_click: function(ev, id) {
        var $menu = $(ev.currentTarget);
        id = $menu.data('menu');
        ev.preventDefault();
        ev.stopPropagation();
        for (var i = 0; i < this.data.data.children.length; i++) {
            if (this.data.data.children[i].id == id) {
                this.children = this.data.data.children[i];
            }
        }
        this.$element
            .removeClass("login_valid")
            .addClass("secondary_menu");
        if(!$('[id^="oe_sec_menu_'+id+'"]').html()){
            $('<div id="oe_sec_menu_'+id+'" data-role="page" data-url="oe_sec_menu_'+id+'"> </div>').appendTo('#moe');
            this.secondary = new instance.web_mobile.Secondary(this, "oe_sec_menu_"+id, this.children);
            this.secondary.start();
        }else{
            $.mobile.changePage('#oe_sec_menu_'+id, "slide", false, true);
        }
    }
});

instance.web_mobile.Secondary =  instance.web.OldWidget.extend({

    template: "Menu.secondary",

    init: function(session, element_id, secondary_menu_id) {
        this._super(session, element_id);
        this.data = secondary_menu_id;
    },
    start: function(ev, id) {
        var self = this;
        var v = { menu : this.data };
        this.$element.html(this.render(v));
        this.$element.find("[data-role=header]").find("h1").html(this.data.name);
        this.$element.add(this.$secondary_menu).find('#content').find("a").click(this.on_menu_click);
        this.$element.find("[data-role=header]").find('#home').click(function(){
            $.mobile.changePage("#oe_menu", "slide", false, true);
        });
        $.mobile.changePage("#"+this.element_id, "slide", false, true);
    },
    on_menu_click: function(ev, id) {
        $menu = $(ev.currentTarget);
        id = $menu.data('menu');
        name = $menu.data('name');
        ev.preventDefault();
        ev.stopPropagation();
        var child_len = 0;
        for (var i = 0; i < this.data.children.length; i++) {
            for (var j=0; j < this.data.children[i].children.length; j++) {
                if (this.data.children[i].children[j].id == id) {
                    this.children = this.data.children[i].children[j];
                    child_len = this.children.children.length;
                }
            }
        }
        if (child_len > 0) {
            this.$element
            .addClass("secondary_menu");
            if(!$('[id^="oe_sec_menu_'+id+'"]').html()){
                $('<div id="oe_sec_menu_'+id+'" data-role="page" data-url="oe_sec_menu_'+id+'"> </div>').appendTo('#moe');
                this.secondary = new instance.web_mobile.Secondary(this, "oe_sec_menu_"+id, this.children);
                this.secondary.start();
            }else{
                $.mobile.changePage('#oe_sec_menu_'+id, "slide", false, true);
            }
        }else {
            if(!$('[id^="oe_list_'+id+'"]').html()){
                $('<div id="oe_list_'+id+'" data-role="page" data-url="oe_list_'+id+'"> </div>').appendTo('#moe');
                this.listview = new instance.web_mobile.ListView(this, "oe_list_"+id, id);
                this.listview.start();
            }else{
                $.mobile.changePage('#oe_list_'+id, "slide", false, true);
            }
        }
        jQuery("#oe_header").find("h1").html($menu.data('name'));
    }
});

instance.web_mobile.Options =  instance.web.OldWidget.extend({

    template: "Options",

    start: function() {
        var self = this;
        this.$element.html(this.render(this));
        this.$element.find("[data-role=header]").find('h1').html('Preference');
        this.$element.find("[data-role=header]").find('#home').click(function(){
            $.mobile.changePage("#oe_menu", "slide", false, true);
        });
        this.$element.find("[data-role=content]").find('a').click(function(){
            $('#oe_login').empty();
            window.location.replace('/mobile');
        });
        $.mobile.changePage("#oe_options", "slide", false, true);
    }
});

};
