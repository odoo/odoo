/*---------------------------------------------------------
 * OpenERP Web chrome
 *---------------------------------------------------------*/
openerp.web.chrome = function(instance) {
var QWeb = instance.web.qweb,
    _t = instance.web._t;

instance.web.Notification =  instance.web.Widget.extend({
    template: 'Notification',
    init: function() {
        this._super.apply(this, arguments);
        instance.web.notification = this;
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.notify({
            speed: 500,
            expires: 2500
        });
    },
    notify: function(title, text, sticky) {
        sticky = !!sticky;
        var opts = {};
        if (sticky) {
            opts.expires = false;
        }
        this.$element.notify('create', {
            title: title,
            text: text
        }, opts);
    },
    warn: function(title, text, sticky) {
        sticky = !!sticky;
        var opts = {};
        if (sticky) {
            opts.expires = false;
        }
        this.$element.notify('create', 'oe_notification_alert', {
            title: title,
            text: text
        }, opts);
    }
});

/**
 * The very minimal function everything should call to create a dialog
 * in OpenERP Web Client.
 */
instance.web.dialog = function(element) {
    var result = element.dialog.apply(element, _.rest(_.toArray(arguments)));
    result.dialog("widget").addClass("openerp");
    return result;
};

instance.web.Dialog = instance.web.Widget.extend({
    dialog_title: "",
    init: function (parent, options, content) {
        var self = this;
        this._super(parent);
        this.content_to_set = content;
        this.dialog_options = {
            modal: true,
            destroy_on_close: true,
            width: 900,
            min_width: 0,
            max_width: '95%',
            height: 'auto',
            min_height: 0,
            max_height: this.get_height('100%') - 200,
            autoOpen: false,
            position: [false, 40],
            buttons: {},
            beforeClose: function () { self.on_close(); },
            resizeStop: this.on_resized
        };
        for (var f in this) {
            if (f.substr(0, 10) == 'on_button_') {
                this.dialog_options.buttons[f.substr(10)] = this[f];
            }
        }
        if (options) {
            _.extend(this.dialog_options, options);
        }
    },
    get_options: function(options) {
        var self = this,
            o = _.extend({}, this.dialog_options, options || {});
        _.each(['width', 'height'], function(unit) {
            o[unit] = self['get_' + unit](o[unit]);
            o['min_' + unit] = self['get_' + unit](o['min_' + unit] || 0);
            o['max_' + unit] = self['get_' + unit](o['max_' + unit] || 0);
            if (o[unit] !== 'auto' && o['min_' + unit] && o[unit] < o['min_' + unit]) o[unit] = o['min_' + unit];
            if (o[unit] !== 'auto' && o['max_' + unit] && o[unit] > o['max_' + unit]) o[unit] = o['max_' + unit];
        });
        if (!o.title && this.dialog_title) {
            o.title = this.dialog_title;
        }
        return o;
    },
    get_width: function(val) {
        return this.get_size(val.toString(), $(window.top).width());
    },
    get_height: function(val) {
        return this.get_size(val.toString(), $(window.top).height());
    },
    get_size: function(val, available_size) {
        if (val === 'auto') {
            return val;
        } else if (val.slice(-1) == "%") {
            return Math.round(available_size / 100 * parseInt(val.slice(0, -1), 10));
        } else {
            return parseInt(val, 10);
        }
    },
    renderElement: function() {
        if (this.content_to_set) {
            this.setElement(this.content_to_set);
        } else if (this.template) {
            this._super();
        }
    },
    open: function(options) {
        if (! this.dialog_inited)
            this.init_dialog();
        var o = this.get_options(options);
        instance.web.dialog(this.$element, o).dialog('open');
        if (o.height === 'auto' && o.max_height) {
            this.$element.css({ 'max-height': o.max_height, 'overflow-y': 'auto' });
        }
        return this;
    },
    init_dialog: function(options) {
        this.renderElement();
        var o = this.get_options(options);
        instance.web.dialog(this.$element, o);
        var res = this.start();
        this.dialog_inited = true;
        return res;
    },
    close: function() {
        this.$element.dialog('close');
    },
    on_close: function() {
        if (this.__tmp_dialog_destroying)
            return;
        if (this.dialog_options.destroy_on_close) {
            this.__tmp_dialog_closing = true;
            this.destroy();
            this.__tmp_dialog_closing = undefined;
        }
    },
    on_resized: function() {
    },
    destroy: function () {
        _.each(this.getChildren(), function(el) {
            el.destroy();
        });
        if (! this.__tmp_dialog_closing) {
            this.__tmp_dialog_destroying = true;
            this.close();
            this.__tmp_dialog_destroying = undefined;
        }
        if (! this.isDestroyed()) {
            this.$element.dialog('destroy');
        }
        this._super();
    }
});

instance.web.CrashManager = instance.web.CallbackEnabled.extend({
    on_rpc_error: function(error) {
        if (error.data.fault_code) {
            var split = ("" + error.data.fault_code).split('\n')[0].split(' -- ');
            if (split.length > 1) {
                error.type = split.shift();
                error.data.fault_code = error.data.fault_code.substr(error.type.length + 4);
            }
        }
        if (error.code === 200 && error.type) {
            this.on_managed_error(error);
        } else {
            this.on_traceback(error);
        }
    },
    on_managed_error: function(error) {
        instance.web.dialog($('<div>' + QWeb.render('CrashManager.warning', {error: error}) + '</div>'), {
            title: "OpenERP " + _.str.capitalize(error.type),
            buttons: [
                {text: _t("Ok"), click: function() { $(this).dialog("close"); }}
            ]
        });
    },
    on_traceback: function(error) {
        var self = this;
        var buttons = {};
        if (instance.session.openerp_entreprise) {
            buttons[_t("Send OpenERP Enterprise Report")] = function() {
                var $this = $(this);
                var issuename = $('#issuename').val();
                var explanation = $('#explanation').val();
                var remark = $('#remark').val();
                // Call the send method from server to send mail with details
                new instance.web.DataSet(self, 'publisher_warranty.contract').call_and_eval('send', [error.data,explanation,remark,issuename]).then(function(result){
                    if (result === false) {
                        alert('There was a communication error.');
                    } else {
                        $this.dialog('close');
                    }
                });
            };
            buttons[_t("Dont send")] = function() {
                $(this).dialog("close");
            };
        } else {
            buttons[_t("Ok")] = function() {
                $(this).dialog("close");
            };
        }
        var dialog = new instance.web.Dialog(this, {
            title: "OpenERP " + _.str.capitalize(error.type),
            width: '80%',
            height: '50%',
            min_width: '800px',
            min_height: '600px',
            buttons: buttons
        }).open();
        dialog.$element.html(QWeb.render('CrashManager.error', {session: instance.session, error: error}));
    },
    on_javascript_exception: function(exception) {
        this.on_traceback({
            type: _t("Client Error"),
            message: exception,
            data: {debug: ""}
        });
    },
});

instance.web.Loading = instance.web.Widget.extend({
    template: 'Loading',
    init: function(parent) {
        this._super(parent);
        this.count = 0;
        this.blocked_ui = false;
        var self = this;
        this.request_call = function() {
            self.on_rpc_event(1);
        };
        this.response_call = function() {
            self.on_rpc_event(-1);
        };
        this.session.on_rpc_request.add_first(this.request_call);
        this.session.on_rpc_response.add_last(this.response_call);
    },
    destroy: function() {
        this.session.on_rpc_request.remove(this.request_call);
        this.session.on_rpc_response.remove(this.response_call);
        this.on_rpc_event(-this.count);
        this._super();
    },
    on_rpc_event : function(increment) {
        var self = this;
        if (!this.count && increment === 1) {
            // Block UI after 3s
            this.long_running_timer = setTimeout(function () {
                self.blocked_ui = true;
                instance.web.blockUI();
            }, 3000);
        }

        this.count += increment;
        if (this.count > 0) {
            if (instance.session.debug) {
                this.$element.text(_.str.sprintf( _t("Loading (%d)"), this.count));
            } else {
                this.$element.text(_t("Loading"));
            }
            this.$element.show();
            this.getParent().$element.addClass('oe_wait');
        } else {
            this.count = 0;
            clearTimeout(this.long_running_timer);
            // Don't unblock if blocked by somebody else
            if (self.blocked_ui) {
                this.blocked_ui = false;
                instance.web.unblockUI();
            }
            this.$element.fadeOut();
            this.getParent().$element.removeClass('oe_wait');
        }
    }
});

instance.web.DatabaseManager = instance.web.Widget.extend({
    init: function(parent) {
        this._super(parent);
        this.unblockUIFunction = instance.web.unblockUI;
        $.validator.addMethod('matches', function (s, _, re) {
            return new RegExp(re).test(s);
        }, _t("Invalid database name"));
    },
    start: function() {
        var self = this;
        $('.oe_secondary_menus_container,.oe_user_menu_placeholder').empty();
        var fetch_db = this.rpc("/web/database/get_list", {}).pipe(
            function(result) {
                self.db_list = result.db_list;
            },
            function (_, ev) {
                ev.preventDefault();
                self.db_list = null;
            });
        var fetch_langs = this.rpc("/web/session/get_lang_list", {}).then(function(result) {
            self.lang_list = result.lang_list;
        });
        return $.when(fetch_db, fetch_langs).then(self.do_render);
    },
    do_render: function() {
        var self = this;
        instance.webclient.toggle_bars(true);
        self.$element.html(QWeb.render("DatabaseManager", { widget : self }));
        $('.oe_user_menu_placeholder').append(QWeb.render("DatabaseManager.user_menu",{ widget : self }));
        $('.oe_secondary_menus_container').append(QWeb.render("DatabaseManager.menu",{ widget : self }));
        $('ul.oe_secondary_submenu > li:first').addClass('oe_active')
        $('ul.oe_secondary_submenu > li').bind('click', function (event) {
            var menuitem = $(this);
            menuitem.addClass('oe_active').siblings().removeClass('oe_active');
            var form_id =menuitem.find('a').attr('href');
            $(form_id).show().siblings().hide();
            event.preventDefault();
        });
        $('#back-to-login').click(self.do_exit);
        self.$element.find("td").addClass("oe_form_group_cell");
        self.$element.find("tr td:first-child").addClass("oe_form_group_cell_label");
        self.$element.find("label").addClass("oe_form_label");
        self.$element.find("form[name=create_db_form]").validate({ submitHandler: self.do_create });
        self.$element.find("form[name=drop_db_form]").validate({ submitHandler: self.do_drop });
        self.$element.find("form[name=backup_db_form]").validate({ submitHandler: self.do_backup });
        self.$element.find("form[name=restore_db_form]").validate({ submitHandler: self.do_restore });
        self.$element.find("form[name=change_pwd_form]").validate({
            messages: {
                old_pwd: "Please enter your previous password",
                new_pwd: "Please enter your new password",
                confirm_pwd: {
                    required: "Please confirm your new password",
                    equalTo: "The confirmation does not match the password"
                }
            },
            submitHandler: self.do_change_password
        });
    },
    destroy: function () {
        this.$element.find('#db-create, #db-drop, #db-backup, #db-restore, #db-change-password, #back-to-login').unbind('click').end().empty();
        this._super();
    },
    /**
     * Converts a .serializeArray() result into a dict. Does not bother folding
     * multiple identical keys into an array, last key wins.
     *
     * @param {Array} array
     */
    to_object: function (array) {
        var result = {};
        _(array).each(function (record) {
            result[record.name] = record.value;
        });
        return result;
    },
    /**
     * Blocks UI and replaces $.unblockUI by a noop to prevent third parties
     * from unblocking the UI
     */
    blockUI: function () {
        instance.web.blockUI();
        instance.web.unblockUI = function () {};
    },
    /**
     * Reinstates $.unblockUI so third parties can play with blockUI, and
     * unblocks the UI
     */
    unblockUI: function () {
        instance.web.unblockUI = this.unblockUIFunction;
        instance.web.unblockUI();
    },
    /**
     * Displays an error dialog resulting from the various RPC communications
     * failing over themselves
     *
     * @param {Object} error error description
     * @param {String} error.title title of the error dialog
     * @param {String} error.error message of the error dialog
     */
    display_error: function (error) {
        return instance.web.dialog($('<div>'), {
            modal: true,
            title: error.title,
            buttons: [
                {text: _t("Ok"), click: function() { $(this).dialog("close"); }}
            ]
        }).html(error.error);
    },
    do_create: function(form) {
        var self = this;
        var fields = $(form).serializeArray();
        self.rpc("/web/database/create", {'fields': fields}, function(result) {
            var form_obj = self.to_object(fields);
            var client_action = {
                type: 'ir.actions.client',
                tag: 'login',
                params: {
                    'db': form_obj['db_name'],
                    'login': 'admin',
                    'password': form_obj['create_admin_pwd'],
                    'login_successful': function() {
                        instance.webclient.show_application();
                    },
                },
            };
            self.do_action(client_action);
        });
    },
    do_drop: function(form) {
        var self = this;
        var $form = $(form),
            fields = $form.serializeArray(),
            $db_list = $form.find('[name=drop_db]'),
            db = $db_list.val();
        if (!db || !confirm("Do you really want to delete the database: " + db + " ?")) {
            return;
        }
        self.rpc("/web/database/drop", {'fields': fields}, function(result) {
            if (result.error) {
                self.display_error(result);
                return;
            }
            self.do_notify("Dropping database", "The database '" + db + "' has been dropped");
            self.start();
        });
    },
    do_backup: function(form) {
        var self = this;
        self.blockUI();
        self.session.get_file({
            form: form,
            success: function () {
                self.do_notify(_t("Backed"), _t("Database backed up successfully"));
            },
            error: function(error){
               if(error){
                  self.display_error({
                        title: 'Backup Database',
                        error: 'AccessDenied'
                  });
               }
            },
            complete: function() {
                self.unblockUI();
            }
        });
    },
    do_restore: function(form) {
        var self = this;
        self.blockUI();
        $(form).ajaxSubmit({
            url: '/web/database/restore',
            type: 'POST',
            resetForm: true,
            success: function (body) {
                // If empty body, everything went fine
                if (!body) { return; }

                if (body.indexOf('403 Forbidden') !== -1) {
                    self.display_error({
                        title: 'Access Denied',
                        error: 'Incorrect super-administrator password'
                    });
                } else {
                    self.display_error({
                        title: 'Restore Database',
                        error: 'Could not restore the database'
                    });
                }
            },
            complete: function() {
                self.unblockUI();
                self.do_notify(_t("Restored"), _t("Database restored successfully"));
            }
        });
    },
    do_change_password: function(form) {
        var self = this;
        self.rpc("/web/database/change_password", {
            'fields': $(form).serializeArray()
        }, function(result) {
            if (result.error) {
                self.display_error(result);
                return;
            }
            self.unblockUI();
            self.do_notify("Changed Password", "Password has been changed successfully");
        });
    },
    do_exit: function () {
        this.$element.remove();
        instance.webclient.toggle_bars(false);
        this.do_action('login');
    }
});
instance.web.client_actions.add("database_manager", "instance.web.DatabaseManager");

instance.web.Login =  instance.web.Widget.extend({
    template: "Login",
    remember_credentials: true,

    init: function(parent, params) {
        this._super(parent);
        this.has_local_storage = typeof(localStorage) != 'undefined';
        this.db_list = null;
        this.selected_db = null;
        this.selected_login = null;
        this.params = params || {};

        if (this.params.login_successful) {
            this.on('login_successful', this, this.params.login_successful);
        }

        if (this.has_local_storage && this.remember_credentials) {
            this.selected_db = localStorage.getItem('last_db_login_success');
            this.selected_login = localStorage.getItem('last_login_login_success');
            if (jQuery.deparam(jQuery.param.querystring()).debug !== undefined) {
                this.selected_password = localStorage.getItem('last_password_login_success');
            }
        }
    },
    start: function() {
        var self = this;
        self.$element.find("form").submit(self.on_submit);
        self.$element.find('.oe_login_manage_db').click(function() {
            self.do_action("database_manager");
        });
        var d;
        if (self.params.db) {
            d = self.do_login(self.params.db, self.params.login, self.params.password);
        } else {
            d = self.rpc("/web/database/get_list", {}).done(self.on_db_loaded).fail(self.on_db_failed);
        }
        return d;
    },
    on_db_loaded: function (result) {
        this.db_list = result.db_list;
        this.$("[name=db]").replaceWith(QWeb.render('Login.dblist', { db_list: this.db_list, selected_db: this.selected_db}));
        if(this.db_list.length === 0) {
            this.do_action("database_manager");
        } else if(this.db_list.length === 1) {
            this.$('div.oe_login_dbpane').hide();
        } else {
            this.$('div.oe_login_dbpane').show();
        }
    },
    on_db_failed: function (error, event) {
        if (error.data.fault_code === 'AccessDenied') {
            event.preventDefault();
        }
    },
    on_submit: function(ev) {
        if(ev) {
            ev.preventDefault();
        }
        var db = this.$("form [name=db]").val();
        if (!db) {
            this.do_warn("Login", "No database selected !");
            return false;
        }
        var login = this.$("form input[name=login]").val();
        var password = this.$("form input[name=password]").val();

        this.do_login(db, login, password);
    },
    /**
     * Performs actual login operation, and UI-related stuff
     *
     * @param {String} db database to log in
     * @param {String} login user login
     * @param {String} password user password
     */
    do_login: function (db, login, password) {
        var self = this;
        this.$element.removeClass('oe_login_invalid');
        self.$(".oe_login_pane").fadeOut("slow");
        return this.session.session_authenticate(db, login, password).pipe(function() {
            if (self.has_local_storage) {
                if(self.remember_credentials) {
                    localStorage.setItem('last_db_login_success', db);
                    localStorage.setItem('last_login_login_success', login);
                    if (jQuery.deparam(jQuery.param.querystring()).debug !== undefined) {
                        localStorage.setItem('last_password_login_success', password);
                    }
                } else {
                    localStorage.setItem('last_db_login_success', '');
                    localStorage.setItem('last_login_login_success', '');
                    localStorage.setItem('last_password_login_success', '');
                }
            }
            self.trigger('login_successful');
        },function () {
            self.$(".oe_login_pane").fadeIn("fast", function() {
                self.$element.addClass("oe_login_invalid");
            });
        });
    },
});
instance.web.client_actions.add("login", "instance.web.Login");

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

/**
 * Client action to go back in breadcrumb history.
 * If can't go back in history stack, will go back to home.
 */
instance.web.HistoryBack = instance.web.Widget.extend({
    init: function(parent, params) {
        if (!parent.history_back()) {
            window.location = '/' + (window.location.search || '');
        }
    }
});
instance.web.client_actions.add("history_back", "instance.web.HistoryBack");

/**
 * Client action to go back home.
 */
instance.web.Home = instance.web.Widget.extend({
    init: function(parent, params) {
        window.location = '/' + (window.location.search || '');
    }
});
instance.web.client_actions.add("home", "instance.web.Home");

instance.web.ChangePassword =  instance.web.Widget.extend({
    template: "ChangePassword",
    start: function() {
        var self = this;
        self.$element.validate({
            submitHandler: function (form) {
                self.rpc("/web/session/change_password",{
                    'fields': $(form).serializeArray()
                }, function(result) {
                    if (result.error) {
                        self.display_error(result);
                        return;
                    } else {
                        instance.webclient.on_logout();
                    }
                });
            }
        });
    },
    display_error: function (error) {
        return instance.web.dialog($('<div>'), {
            modal: true,
            title: error.title,
            buttons: [
                {text: _t("Ok"), click: function() { $(this).dialog("close"); }}
            ]
        }).html(error.error);
    },
})
instance.web.client_actions.add("change_password", "instance.web.ChangePassword");

instance.web.Menu =  instance.web.Widget.extend({
    template: 'Menu',
    init: function() {
        this._super.apply(this, arguments);
        this.has_been_loaded = $.Deferred();
        this.maximum_visible_links = 'auto'; // # of menu to show. 0 = do not crop, 'auto' = algo
        this.data = {data:{children:[]}};
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$secondary_menus = this.getParent().$element.find('.oe_secondary_menus_container');
        this.$secondary_menus.on('click', 'a[data-menu]', this.on_menu_click);
        return this.do_reload();
    },
    do_reload: function() {
        return this.rpc("/web/menu/load", {}).then(this.on_loaded);
    },
    on_loaded: function(data) {
        var self = this;
        this.data = data;
        this.renderElement();
        this.limit_entries();
        this.$secondary_menus.html(QWeb.render("Menu.secondary", { widget : this }));
        this.$element.on('click', 'a[data-menu]', this.on_menu_click);
        // Hide second level submenus
        this.$secondary_menus.find('.oe_menu_toggler').siblings('.oe_secondary_submenu').hide();
        if (self.current_menu) {
            self.open_menu(self.current_menu);
        }
        this.has_been_loaded.resolve();
    },
    limit_entries: function() {
        var maximum_visible_links = this.maximum_visible_links;
        if (maximum_visible_links === 'auto') {
            maximum_visible_links = this.auto_limit_entries();
        }
        if (maximum_visible_links < this.data.data.children.length) {
            var $more = $(QWeb.render('Menu.more')),
                $index = this.$element.find('li').eq(maximum_visible_links - 1);
            $index.after($more);
            $more.find('.oe_menu_more').append($index.next().nextAll());
        }
    },
    auto_limit_entries: function() {
        // TODO: auto detect overflow and bind window on resize
        var width = $(window).width();
        return Math.floor(width / 125);
    },
    /**
     * Opens a given menu by id, as if a user had browsed to that menu by hand
     * except does not trigger any event on the way
     *
     * @param {Number} id database id of the terminal menu to select
     */
    open_menu: function (id) {
        var $clicked_menu, $sub_menu, $main_menu;
        $clicked_menu = this.$element.add(this.$secondary_menus).find('a[data-menu=' + id + ']');
        this.trigger('open_menu', id, $clicked_menu);

        if (this.$secondary_menus.has($clicked_menu).length) {
            $sub_menu = $clicked_menu.parents('.oe_secondary_menu');
            $main_menu = this.$element.find('a[data-menu=' + $sub_menu.data('menu-parent') + ']');
        } else {
            $sub_menu = this.$secondary_menus.find('.oe_secondary_menu[data-menu-parent=' + $clicked_menu.attr('data-menu') + ']');
            $main_menu = $clicked_menu;
        }

        // Activate current main menu
        this.$element.find('.oe_active').removeClass('oe_active');
        $main_menu.addClass('oe_active');

        // Show current sub menu
        this.$secondary_menus.find('.oe_secondary_menu').hide();
        $sub_menu.show();

        // Hide/Show the leftbar menu depending of the presence of sub-items
        this.$secondary_menus.parent('.oe_leftbar').toggle(!!$sub_menu.children().length);

        // Activate current menu item and show parents
        this.$secondary_menus.find('.oe_active').removeClass('oe_active');
        if ($main_menu !== $clicked_menu) {
            $clicked_menu.parents().show();
            if ($clicked_menu.is('.oe_menu_toggler')) {
                $clicked_menu.toggleClass('oe_menu_opened').siblings('.oe_secondary_submenu:first').toggle();
            } else {
                $clicked_menu.parent().addClass('oe_active');
            }
        }
    },
    /**
     * Call open_menu with the first menu_item matching an action_id
     *
     * @param {Number} id the action_id to match
     */
    open_action: function (id) {
        var $menu = this.$element.add(this.$secondary_menus).find('a[data-action-id="' + id + '"]');
        var menu_id = $menu.data('menu');
        if (menu_id) {
            this.open_menu(menu_id);
        }
    },
    /**
     * Process a click on a menu item
     *
     * @param {Number} id the menu_id
     * @param {Boolean} [needaction=false] whether the triggered action should execute in a `needs action` context
     */
    menu_click: function(id, needaction) {
        if (!id) { return; }

        // find back the menuitem in dom to get the action
        var $item = this.$element.find('a[data-menu=' + id + ']');
        if (!$item.length) {
            $item = this.$secondary_menus.find('a[data-menu=' + id + ']');
        }
        var action_id = $item.data('action-id');
        // If first level menu doesnt have action trigger first leaf
        if (!action_id) {
            if(this.$element.has($item).length) {
                var $sub_menu = this.$secondary_menus.find('.oe_secondary_menu[data-menu-parent=' + id + ']');
                var $items = $sub_menu.find('a[data-action-id]').filter('[data-action-id!=""]');
                if($items.length) {
                    action_id = $items.data('action-id');
                    id = $items.data('menu');
                }
            }
        }
        this.open_menu(id);
        this.current_menu = id;
        this.session.active_id = id;
        if (action_id) {
            this.trigger('menu_click', {
                action_id: action_id,
                needaction: needaction,
                id: id
            }, $item);
        }
    },
    /**
     * Jquery event handler for menu click
     *
     * @param {Event} ev the jquery event
     */
    on_menu_click: function(ev) {
        ev.preventDefault();
        var needaction = $(ev.target).is('div.oe_menu_counter');
        this.menu_click($(ev.currentTarget).data('menu'), needaction);
    },
});

instance.web.UserMenu =  instance.web.Widget.extend({
    template: "UserMenu",
    init: function(parent) {
        this._super(parent);
        this.update_promise = $.Deferred().resolve();
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);
        this.$element.on('click', '.oe_dropdown_menu li a[data-menu]', function(ev) {
            ev.preventDefault();
            var f = self['on_menu_' + $(this).data('menu')];
            if (f) {
                f($(this));
            }
        });
    },
    do_update: function () {
        var self = this;
        var fct = function() {
            var $avatar = self.$element.find('.oe_topbar_avatar');
            $avatar.attr('src', $avatar.data('default-src'));
            if (!self.session.uid)
                return;
            var func = new instance.web.Model("res.users").get_func("read");
            return func(self.session.uid, ["name", "company_id"]).pipe(function(res) {
                var topbar_name = res.name;
                if(instance.session.debug)
                    topbar_name = _.str.sprintf("%s (%s)", topbar_name, instance.session.db);
                if(res.company_id[0] > 1)
                    topbar_name = _.str.sprintf("%s (%s)", topbar_name, res.company_id[1]);
                self.$element.find('.oe_topbar_name').text(topbar_name);
                var avatar_src = _.str.sprintf('%s/web/binary/image?session_id=%s&model=res.users&field=image_small&id=%s', self.session.prefix, self.session.session_id, self.session.uid);
                $avatar.attr('src', avatar_src);
            });
        };
        this.update_promise = this.update_promise.pipe(fct, fct);
    },
    on_action: function() {
    },
    on_menu_logout: function() {
    },
    on_menu_settings: function() {
        var self = this;
        self.rpc("/web/action/load", { action_id: "base.action_res_users_my" }, function(result) {
            result.result.res_id = instance.session.uid;
            self.getParent().action_manager.do_action(result.result);
        });
    },
    on_menu_about: function() {
        var self = this;
        self.rpc("/web/webclient/version_info", {}).then(function(res) {
            var $help = $(QWeb.render("UserMenu.about", {version_info: res}));
            $help.find('a.oe_activate_debug_mode').click(function (e) {
                e.preventDefault();
                window.location = $.param.querystring(
                        window.location.href, 'debug');
            });
            instance.web.dialog($help, {autoOpen: true,
                modal: true, width: 507, height: 290, resizable: false, title: _t("About")});
        });
    },
});

instance.web.Client = instance.web.Widget.extend({
    init: function(parent, origin) {
        instance.client = instance.webclient = this;
        this._super(parent);
        this.origin = origin;
    },
    start: function() {
        var self = this;
        return instance.session.session_bind(this.origin).pipe(function() {
            var $e = $(QWeb.render(self._template, {}));
            self.replaceElement($e);
            self.bind_events();
            return self.show_common();
        });
    },
    bind_events: function() {
        var self = this;
        this.$element.on('mouseenter', '.oe_systray > div:not([data-tipsy=true])', function() {
            $(this).attr('data-tipsy', 'true').tipsy().trigger('mouseenter');
        });
        this.$element.on('click', '.oe_dropdown_toggle', function(ev) {
            ev.preventDefault();
            var $toggle = $(this);
            var $menu = $toggle.siblings('.oe_dropdown_menu');
            $menu = $menu.size() >= 1 ? $menu : $toggle.find('.oe_dropdown_menu');
            var state = $menu.is('.oe_opened');
            setTimeout(function() {
                // Do not alter propagation
                $toggle.add($menu).toggleClass('oe_opened', !state);
                if (!state) {
                    // Move $menu if outside window's edge
                    var doc_width = $(document).width();
                    var offset = $menu.offset();
                    var menu_width = $menu.width();
                    var x = doc_width - offset.left - menu_width - 2;
                    if (x < 0) {
                        $menu.offset({ left: offset.left + x }).width(menu_width);
                    }
                }
            }, 0);
        });
        instance.web.bus.on('click', this, function(ev) {
            $.fn.tipsy.clear();
            if (!$(ev.target).is('input[type=file]')) {
                self.$element.find('.oe_dropdown_menu.oe_opened, .oe_dropdown_toggle.oe_opened').removeClass('oe_opened');
            }
        });
    },
    show_common: function() {
        var self = this;
        this.crashmanager =  new instance.web.CrashManager();
        instance.session.on_rpc_error.add(this.crashmanager.on_rpc_error);
        self.notification = new instance.web.Notification(this);
        self.notification.appendTo(self.$element);
        self.loading = new instance.web.Loading(self);
        self.loading.appendTo(self.$element);
        self.action_manager = new instance.web.ActionManager(self);
        self.action_manager.appendTo(self.$('.oe_application'));
    },
    toggle_bars: function(value) {
        this.$('tr:has(td.oe_topbar),.oe_leftbar').toggle(value);
    }
});

instance.web.WebClient = instance.web.Client.extend({
    _template: 'WebClient',
    init: function(parent) {
        this._super(parent);
        this._current_state = null;
    },
    start: function() {
        var self = this;
        return $.when(this._super()).pipe(function() {
            if (jQuery.param !== undefined && jQuery.deparam(jQuery.param.querystring()).kitten !== undefined) {
                $("body").addClass("kitten-mode-activated");
                if ($.blockUI) {
                    $.blockUI.defaults.message = '<img src="http://www.amigrave.com/kitten.gif">';
                }
            }
            if (!self.session.session_is_valid()) {
                self.show_login();
            } else {
                self.show_application();
            }
        });
    },
    set_title: function(title) {
        title = _.str.clean(title);
        var sep = _.isEmpty(title) ? '' : ' - ';
        document.title = title + sep + 'OpenERP';
    },
    show_common: function() {
        var self = this;
        this._super();
        window.onerror = function (message, file, line) {
            self.crashmanager.on_traceback({
                type: _t("Client Error"),
                message: message,
                data: {debug: file + ':' + line}
            });
        };
    },
    show_login: function() {
        this.toggle_bars(false);
        
        var action = {
            'type': 'ir.actions.client',
            'tag': 'login'
        };
        var state = $.bbq.getState(true);
        if (state.action === "login") {
            action.params = state;
        }

        this.action_manager.do_action(action);
        this.action_manager.inner_widget.on('login_successful', this, function() {
            this.do_push_state(state);
            this._current_state = null;     // ensure the state will be loaded
            this.show_application();        // will load the state we just pushed
        });
    },
    show_application: function() {
        var self = this;
        self.toggle_bars(true);
        self.menu = new instance.web.Menu(self);
        self.menu.replace(this.$element.find('.oe_menu_placeholder'));
        self.menu.on('menu_click', this, this.on_menu_action);
        self.user_menu = new instance.web.UserMenu(self);
        self.user_menu.replace(this.$element.find('.oe_user_menu_placeholder'));
        self.user_menu.on_menu_logout.add(this.proxy('on_logout'));
        self.user_menu.on_action.add(this.proxy('on_menu_action'));
        self.user_menu.do_update();
        self.bind_hashchange();
        if (!self.session.openerp_entreprise) {
            var version_label = _t("OpenERP - Unsupported/Community Version");
            self.$element.find('.oe_footer_powered').append(_.str.sprintf('<span> - <a href="http://www.openerp.com/support-or-publisher-warranty-contract" target="_blank">%s</a></span>', version_label));
        }
        self.set_title();
    },
    destroy_content: function() {
        _.each(_.clone(this.getChildren()), function(el) {
            el.destroy();
        });
        this.$element.children().remove();
    },
    do_reload: function() {
        var self = this;
        return this.session.session_reload().pipe(function () {
            instance.session.load_modules(true).pipe(
                self.menu.proxy('do_reload')); });

    },
    do_notify: function() {
        var n = this.notification;
        n.notify.apply(n, arguments);
    },
    do_warn: function() {
        var n = this.notification;
        n.warn.apply(n, arguments);
    },
    on_logout: function() {
        var self = this;
        this.session.session_logout().then(function () {
            $(window).unbind('hashchange', self.on_hashchange);
            self.do_push_state({});
            window.location.reload();
        });
    },
    bind_hashchange: function() {
        var self = this;
        $(window).bind('hashchange', this.on_hashchange);

        var state = $.bbq.getState(true);
        if (_.isEmpty(state) || state.action == "login") {
            self.menu.has_been_loaded.then(function() {
                var first_menu_id = self.menu.$element.find("a:first").data("menu");
                if(first_menu_id) {
                    self.menu.menu_click(first_menu_id);
                }
            });
        } else {
            $(window).trigger('hashchange');
        }
    },
    on_hashchange: function(event) {
        var self = this;
        var state = event.getState(true);
        if (!_.isEqual(this._current_state, state)) {
            if(state.action_id === undefined && state.menu_id) {
                self.menu.has_been_loaded.then(function() {
                    self.menu.do_reload().then(function() {
                        self.menu.menu_click(state.menu_id)
                    });
                });
            } else {
                this.action_manager.do_load_state(state, !!this._current_state);
            }
        }
        this._current_state = state;
    },
    do_push_state: function(state) {
        this.set_title(state.title);
        delete state.title;
        var url = '#' + $.param(state);
        this._current_state = _.clone(state);
        $.bbq.pushState(url);
    },
    on_menu_action: function(options) {
        var self = this;
        this.rpc("/web/action/load", { action_id: options.action_id })
            .then(function (result) {
                var action = result.result;
                if (options.needaction) {
                    action.context.search_default_needaction_pending = true;
                }
                self.action_manager.clear_breadcrumbs();
                self.action_manager.do_action(action);
            });
    },
    do_action: function(action) {
        var self = this;
        // TODO replace by client action menuclick
        if(action.menu_id) {
            this.do_reload().then(function () {
                self.menu.menu_click(action.menu_id);
            });
        }
    },
    set_content_full_screen: function(fullscreen) {
        if (fullscreen) {
            $(".oe_webclient", this.$element).addClass("oe_content_full_screen");
            $("body").css({'overflow-y':'hidden'});
        } else {
            $(".oe_webclient", this.$element).removeClass("oe_content_full_screen");
            $("body").css({'overflow-y':'scroll'});
        }
    }
});

instance.web.EmbeddedClient = instance.web.Client.extend({
    _template: 'EmbedClient',
    init: function(parent, origin, dbname, login, key, action_id, options) {
        this._super(parent, origin);

        this.dbname = dbname;
        this.login = login;
        this.key = key;
        this.action_id = action_id;
        this.options = options || {};
    },
    start: function() {
        var self = this;
        return $.when(this._super()).pipe(function() {
            return instance.session.session_authenticate(self.dbname, self.login, self.key, true).pipe(function() {
                return self.rpc("/web/action/load", { action_id: self.action_id }, function(result) {
                    var action = result.result;
                    action.flags = _.extend({
                        //views_switcher : false,
                        search_view : false,
                        action_buttons : false,
                        sidebar : false
                        //pager : false
                    }, self.options, action.flags || {});

                    self.action_manager.do_action(action);
                });
            });
        });
    },
});

instance.web.embed = function (origin, dbname, login, key, action, options) {
    $('head').append($('<link>', {
        'rel': 'stylesheet',
        'type': 'text/css',
        'href': origin +'/web/webclient/css'
    }));
    var currentScript = document.currentScript;
    if (!currentScript) {
        var sc = document.getElementsByTagName('script');
        currentScript = sc[sc.length-1];
    }
    var client = new instance.web.EmbeddedClient(null, origin, dbname, login, key, action, options);
    client.insertAfter(currentScript);
};

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
