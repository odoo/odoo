/*---------------------------------------------------------
 * OpenERP Web chrome
 *---------------------------------------------------------*/
openerp.web.chrome = function(openerp) {
var QWeb = openerp.web.qweb;

openerp.web.Notification =  openerp.web.Widget.extend(/** @lends openerp.web.Notification# */{
    template: 'Notification',
    identifier_prefix: 'notification-',

    init: function() {
        this._super.apply(this, arguments);
        openerp.notification = this;
    },

    start: function() {
        this._super.apply(this, arguments);
        this.$element.notify({
            speed: 500,
            expires: 1500
        });
    },
    notify: function(title, text) {
        this.$element.notify('create', {
            title: title,
            text: text
        });
    },
    warn: function(title, text) {
        this.$element.notify('create', 'oe_notification_alert', {
            title: title,
            text: text,
        }, {
            expires: false,
        });
    },

});

openerp.web.Dialog = openerp.web.OldWidget.extend(/** @lends openerp.web.Dialog# */{
    dialog_title: "",
    identifier_prefix: 'dialog',
    /**
     * @constructs openerp.web.Dialog
     * @extends openerp.web.OldWidget
     *
     * @param parent
     * @param dialog_options
     */
    init: function (parent, dialog_options) {
        var self = this;
        this._super(parent);
        this.dialog_options = {
            modal: true,
            width: 'auto',
            min_width: 0,
            max_width: '100%',
            height: 'auto',
            min_height: 0,
            max_height: '100%',
            autoOpen: false,
            buttons: {},
            beforeClose: function () { self.on_close(); }
        };
        for (var f in this) {
            if (f.substr(0, 10) == 'on_button_') {
                this.dialog_options.buttons[f.substr(10)] = this[f];
            }
        }
        if (dialog_options) {
            this.set_options(dialog_options);
        }
    },
    set_options: function(options) {
        options = options || {};
        options.width = this.get_width(options.width || this.dialog_options.width);
        options.min_width = this.get_width(options.min_width || this.dialog_options.min_width);
        options.max_width = this.get_width(options.max_width || this.dialog_options.max_width);
        options.height = this.get_height(options.height || this.dialog_options.height);
        options.min_height = this.get_height(options.min_height || this.dialog_options.min_height);
        options.max_height = this.get_height(options.max_height || this.dialog_options.max_width);

        if (options.width !== 'auto') {
            if (options.width > options.max_width) options.width = options.max_width;
            if (options.width < options.min_width) options.width = options.min_width;
        }
        if (options.height !== 'auto') {
            if (options.height > options.max_height) options.height = options.max_height;
            if (options.height < options.min_height) options.height = options.min_height;
        }
        if (!options.title && this.dialog_title) {
            options.title = this.dialog_title;
        }
        _.extend(this.dialog_options, options);
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
    start: function () {
        this.$dialog = $('<div id="' + this.element_id + '"></div>').dialog(this.dialog_options);
        this._super();
        return this;
    },
    open: function(dialog_options) {
        // TODO fme: bind window on resize
        if (this.template) {
            this.$element.html(this.render());
        }
        this.set_options(dialog_options);
        this.$dialog.dialog(this.dialog_options).dialog('open');
        return this;
    },
    close: function() {
        // Closes the dialog but leave it in a state where it could be opened again.
        this.$dialog.dialog('close');
    },
    on_close: function() {
    },
    stop: function () {
        // Destroy widget
        this.close();
        this.$dialog.dialog('destroy');
        this._super();
    }
});

openerp.web.CrashManager = openerp.web.Dialog.extend(/** @lends openerp.web.CrashManager# */{
    identifier_prefix: 'dialog_crash',
    /**
     * @constructs opener.web.CrashManager
     * @extends openerp.web.Dialog
     *
     * @param parent
     */
    init: function(parent) {
        this._super(parent);
        this.session.on_rpc_error.add(this.on_rpc_error);
    },
    on_button_Ok: function() {
        this.close();
    },
    on_rpc_error: function(error) {
        this.error = error;
        if (error.data.fault_code) {
            var split = ("" + error.data.fault_code).split('\n')[0].split(' -- ');
            if (split.length > 1) {
                error.type = split.shift();
                error.data.fault_code = error.data.fault_code.substr(error.type.length + 4);
            }
        }
        if (error.code === 200 && error.type) {
            this.dialog_title = "OpenERP " + _.capitalize(error.type);
            this.template = 'DialogWarning';
            this.open({
                width: 'auto',
                height: 'auto'
            });
        } else {
            this.dialog_title = "OpenERP Error";
            this.template = 'DialogTraceback';
            this.open({
                width: 'auto',
                height: 'auto'
            });
        }
    }
});

openerp.web.Loading =  openerp.web.Widget.extend(/** @lends openerp.web.Loading# */{
    /**
     * @constructs openerp.web.Loading
     * @extends openerp.web.Widget
     *
     * @param parent
     * @param element_id
     */
    init: function(parent, element_id) {
        this._super(parent, element_id);
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

openerp.web.Database = openerp.web.Widget.extend(/** @lends openerp.web.Database# */{
    /**
     * @constructs openerp.web.Database
     * @extends openerp.web.Widget
     *
     * @param parent
     * @param element_id
     * @param option_id
     */
    init: function(parent, element_id, option_id) {
        this._super(parent, element_id);
        this.$option_id = $('#' + option_id);
    },
    start: function() {
        this.$element.html(QWeb.render("Database", this));
        this.$element.closest(".openerp")
                .removeClass("login-mode")
                .addClass("database_block");

        var self = this;
        var fetch_db = this.rpc("/web/database/get_list", {}, function(result) {
            self.db_list = result.db_list;
        });
        var fetch_langs = this.rpc("/web/session/get_lang_list", {}, function(result) {
            if (result.error) {
                self.display_error(result);
                return;
            }
            self.lang_list = result.lang_list;
        });
        $.when(fetch_db, fetch_langs).then(function () {self.do_create();});

        this.$element.find('#db-create').click(this.do_create);
        this.$element.find('#db-drop').click(this.do_drop);
        this.$element.find('#db-backup').click(this.do_backup);
        this.$element.find('#db-restore').click(this.do_restore);
        this.$element.find('#db-change-password').click(this.do_change_password);
       	this.$element.find('#back-to-login').click(function() {
            self.stop();
        });
    },
    stop: function () {
        this.$option_id.empty();

        this.$element
            .find('#db-create, #db-drop, #db-backup, #db-restore, #db-change-password, #back-to-login')
                .unbind('click')
            .end()
            .closest(".openerp")
                .addClass("login-mode")
                .removeClass("database_block")
            .end()
            .empty();
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
     * Waits until the new database is done creating, then unblocks the UI and
     * logs the user in as admin
     *
     * @param {Number} db_creation_id identifier for the db-creation operation, used to fetch the current installation progress
     * @param {Object} info info fields for this database creation
     * @param {String} info.db name of the database being created
     * @param {String} info.password super-admin password for the database
     */
    wait_for_newdb: function (db_creation_id, info) {
        var self = this;
        self.rpc('/web/database/progress', {
            id: db_creation_id,
            password: info.password
        }, function (result) {
            var progress = result[0];
            // I'd display a progress bar, but turns out the progress status
            // the server report kind-of blows goats: it's at 0 for ~75% of
            // the installation, then jumps to 75%, then jumps down to either
            // 0 or ~40%, then back up to 75%, then terminates. Let's keep that
            // mess hidden behind a not-very-useful but not overly weird
            // message instead.
            if (progress < 1) {
                setTimeout(function () {
                    self.wait_for_newdb(db_creation_id, info);
                }, 500);
                return;
            }

            var admin = result[1][0];
            setTimeout(function () {
                self.widget_parent.do_login(
                        info.db, admin.login, admin.password);
                self.stop();
                $.unblockUI();
            });
        });
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
        return $('<div>').dialog({
            modal: true,
            title: error.title,
            buttons: {
                Ok: function() {
                    $(this).dialog("close");
                }
            }
        }).html(error.error);
    },
    do_create: function() {
        var self = this;
       	self.$option_id.html(QWeb.render("Database.CreateDB", self));
        self.$option_id.find("form[name=create_db_form]").validate({
            submitHandler: function (form) {
                var fields = $(form).serializeArray();
                $.blockUI({message:'<img src="/web/static/src/img/throbber2.gif">'});
                self.rpc("/web/database/create", {'fields': fields}, function(result) {
                    if (result.error) {
                        $.unblockUI();
                        self.display_error(result);
                        return;
                    }
                    self.db_list.push(self.to_object(fields)['db_name']);
                    self.db_list.sort();
                    var form_obj = self.to_object(fields);
                    self.wait_for_newdb(result, {
                        password: form_obj['super_admin_pwd'],
                        db: form_obj['db_name']
                    });
                });
            }
        });
    },
    do_drop: function() {
        var self = this;
       	self.$option_id.html(QWeb.render("DropDB", self));
       	self.$option_id.find("form[name=drop_db_form]").validate({
            submitHandler: function (form) {
                var $form = $(form),
                    fields = $form.serializeArray(),
                    $db_list = $form.find('select[name=drop_db]'),
                    db = $db_list.val();

                if (!confirm("Do you really want to delete the database: " + db + " ?")) {
                    return;
                }
                self.rpc("/web/database/drop", {'fields': fields}, function(result) {
                    if (result.error) {
                        self.display_error(result);
                        return;
                    }
                    $db_list.find(':selected').remove();
                    self.db_list.splice(_.indexOf(self.db_list, db, true), 1);
                    self.do_notify("Dropping database", "The database '" + db + "' has been dropped");
                });
            }
        });
    },
    do_backup: function() {
        var self = this;
       	self.$option_id
            .html(QWeb.render("BackupDB", self))
            .find("form[name=backup_db_form]").validate({
            submitHandler: function (form) {
                $.blockUI({message:'<img src="/web/static/src/img/throbber2.gif">'});
                self.session.get_file({
                    form: form,
                    error: function (body) {
                        var error = body.firstChild.data.split('|');
                        self.display_error({
                            title: error[0],
                            error: error[1]
                        });
                    },
                    complete: $.unblockUI
                });
            }
        });
    },
    do_restore: function() {
        var self = this;
       	self.$option_id.html(QWeb.render("RestoreDB", self));

       	self.$option_id.find("form[name=restore_db_form]").validate({
            submitHandler: function (form) {
                $.blockUI({message:'<img src="/web/static/src/img/throbber2.gif">'});
                $(form).ajaxSubmit({
                    url: '/web/database/restore',
                    type: 'POST',
                    resetForm: true,
                    success: function (body) {
                        // TODO: ui manipulations
                        // note: response objects don't work, but we have the
                        // HTTP body of the response~~

                        // If empty body, everything went fine
                        if (!body) { return; }

                        if (body.indexOf('403 Forbidden') !== -1) {
                            self.display_error({
                                title: 'Access Denied',
                                error: 'Incorrect super-administrator password'
                            })
                        } else {
                            self.display_error({
                                title: 'Restore Database',
                                error: 'Could not restore the database'
                            })
                        }
                    },
                    complete: function () {
                        $.unblockUI();
                    }
                });
            }
        });
    },
    do_change_password: function() {
        var self = this;
       	self.$option_id.html(QWeb.render("Change_DB_Pwd", self));

        self.$option_id.find("form[name=change_pwd_form]").validate({
            messages: {
                old_pwd: "Please enter your previous password",
                new_pwd: "Please enter your new password",
                confirm_pwd: {
                    required: "Please confirm your new password",
                    equalTo: "The confirmation does not match the password"
                }
            },
            submitHandler: function (form) {
                self.rpc("/web/database/change_password", {
                    'fields': $(form).serializeArray()
                }, function(result) {
                    if (result.error) {
                        self.display_error(result);
                        return;
                    }
                    self.do_notify("Changed Password", "Password has been changed successfully");
                });
            }
        });
    }
});

openerp.web.Login =  openerp.web.Widget.extend(/** @lends openerp.web.Login# */{
    remember_creditentials: true,
    
    template: "Login",
    identifier_prefix: 'oe-app-login-',
    /**
     * @constructs openerp.web.Login
     * @extends openerp.web.Widget
     *
     * @param parent
     * @param element_id
     */

    init: function(parent) {
        this._super(parent);
        this.has_local_storage = typeof(localStorage) != 'undefined';
        this.selected_db = null;
        this.selected_login = null;

        if (this.has_local_storage && this.remember_creditentials) {
            this.selected_db = localStorage.getItem('last_db_login_success');
            this.selected_login = localStorage.getItem('last_login_login_success');
            if (jQuery.deparam(jQuery.param.querystring()).debug != undefined) {
                this.selected_password = localStorage.getItem('last_password_login_success');
            }
        }
        
        var qs = jQuery.deparam(jQuery.param.querystring());
        if (qs.db) {
            this.selected_db = qs.db;
        }
        if (qs.login) {
            this.selected_login = qs.login;
        }

    },
    start: function() {
        var self = this;
        this.database = new openerp.web.Database(
                this, "oe_database", "oe_db_options");

        this.$element.find('#oe-db-config').click(function() {
            self.database.start();
        });

        this.$element.find("form").submit(this.on_submit);

        this.rpc("/web/database/get_list", {}, function(result) {
            var tpl = openerp.web.qweb.render('Login_dblist', {db_list: result.db_list, selected_db: self.selected_db});
            self.$element.find("input[name=db]").replaceWith(tpl)
        }, 
        function(error, event) {
            if (error.data.fault_code === 'AccessDenied') {
                event.preventDefault();
            }
        });

    },
    on_login_invalid: function() {
        this.$element.closest(".openerp").addClass("login-mode");
    },
    on_login_valid: function() {
        this.$element.closest(".openerp").removeClass("login-mode");
    },
    on_submit: function(ev) {
        ev.preventDefault();
        var $e = this.$element;
        var db = $e.find("form [name=db]").val();
        var login = $e.find("form input[name=login]").val();
        var password = $e.find("form input[name=password]").val();

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
        this.session.session_login(db, login, password, function() {
            if(self.session.session_is_valid()) {
                if (self.has_local_storage) {
                    if(self.remember_creditentials) {
                        localStorage.setItem('last_db_login_success', db);
                        localStorage.setItem('last_login_login_success', login);
                        if (jQuery.deparam(jQuery.param.querystring()).debug != undefined) {
                            localStorage.setItem('last_password_login_success', password);
                        }
                    } else {
                        localStorage.setItem('last_db_login_success', '');
                        localStorage.setItem('last_login_login_success', '');
                        localStorage.setItem('last_password_login_success', '');
                    }
                }
                self.on_login_valid();
            } else {
                self.$element.addClass("login_invalid");
                self.on_login_invalid();
            }
        });
    },
    do_ask_login: function(continuation) {
        this.on_login_invalid();
        this.$element
            .removeClass("login_invalid");
        this.on_login_valid.add({
            position: "last",
            unique: true,
            callback: continuation || function() {}
        });
    },
    on_logout: function() {
        this.session.logout();
    }
});

openerp.web.Header =  openerp.web.Widget.extend(/** @lends openerp.web.Header# */{
    template: "Header",
    identifier_prefix: 'oe-app-header-',
    /**
     * @constructs openerp.web.Header
     * @extends openerp.web.Widget
     *
     * @param parent
     */
    init: function(parent) {
        this._super(parent);
        this.qs = "?" + jQuery.param.querystring();
        this.$content = $();
        this.update_promise = $.Deferred().resolve();
    },
    start: function() {
        this._super();
    },
    do_update: function () {
        var self = this;
        var fct = function() {
            self.$content.remove();
            if (!self.session.uid)
                return;
            var func = new openerp.web.Model(self.session, "res.users").get_func("read");
            return func(self.session.uid, ["name", "company_id"]).pipe(function(res) {
                self.$content = $(QWeb.render("Header-content", {widget: self, user: res}));
                self.$content.appendTo(self.$element);
                self.$element.find(".logout").click(self.on_logout);
                self.$element.find("a.preferences").click(self.on_preferences);
                self.$element.find(".about").click(self.on_about);
                return self.shortcut_load();
            });
        };
        this.update_promise = this.update_promise.pipe(fct, fct);
    },
    on_about: function() {
        var self = this;
        self.rpc("/web/webclient/version_info", {}).then(function(res) {
            var $help = $(QWeb.render("About-Page", {version_info: res}));
            $help.dialog({autoOpen: true,
                modal: true, width: 960, title: "About"});
        });
    },
    shortcut_load :function(){
        var self = this,
            sc = self.session.shortcuts,
            shortcuts_ds = new openerp.web.DataSet(this, 'ir.ui.view_sc');
        // TODO: better way to communicate between sections.
        // sc.bindings, because jquery does not bind/trigger on arrays...
        if (!sc.binding) {
            sc.binding = {};
            $(sc.binding).bind({
                'add': function (e, attrs) {
                    shortcuts_ds.create(attrs, function (out) {
                        $('<li>', {
                            'data-shortcut-id':out.result,
                            'data-id': attrs.res_id
                        }).text(attrs.name)
                          .appendTo(self.$element.find('.oe-shortcuts ul'));
                        attrs.id = out.result;
                        sc.push(attrs);
                    });
                },
                'remove-current': function () {
                    var menu_id = self.session.active_id;
                    var $shortcut = self.$element
                        .find('.oe-shortcuts li[data-id=' + menu_id + ']');
                    var shortcut_id = $shortcut.data('shortcut-id');
                    $shortcut.remove();
                    shortcuts_ds.unlink([shortcut_id]);
                    var sc_new = _.reject(sc, function(shortcut){ return shortcut_id === shortcut.id});
                    sc.splice(0, sc.length);
                    sc.push.apply(sc, sc_new);
                    }
            });
        }
        return this.rpc('/web/session/sc_list', {}, function(shortcuts) {
            sc.splice(0, sc.length);
            sc.push.apply(sc, shortcuts);

            self.$element.find('.oe-shortcuts')
                .html(QWeb.render('Shortcuts', {'shortcuts': shortcuts}))
                .undelegate('li', 'click')

                .delegate('li', 'click', function(e) {
                    e.stopPropagation();
                    var id = $(this).data('id');
                    self.session.active_id = id;
                    self.rpc('/web/menu/action', {'menu_id':id}, function(ir_menu_data) {
                        if (ir_menu_data.action.length){
                            self.on_action(ir_menu_data.action[0][2]);
                        }
                    });
                });
        });
    },

    on_action: function(action) {
    },
    on_preferences: function(){
        var self = this;
        var action_manager = new openerp.web.ActionManager(this);
        var dataset = new openerp.web.DataSet (this,'res.users',this.context);
        dataset.call ('action_get','',function (result){
            self.rpc('/web/action/load', {action_id:result}, function(result){
                action_manager.do_action(_.extend(result['result'], {
                    res_id: self.session.uid,
                    res_model: 'res.users',
                    flags: {
                        action_buttons: false,
                        search_view: false,
                        sidebar: false,
                        views_switcher: false,
                        pager: false
                    }
                }));
            });
        });
        this.dialog = new openerp.web.Dialog(this,{
            modal: true,
            title: 'Preferences',
            width: 600,
            height: 500,
            buttons: {
                "Change password": function(){
                    self.change_password();
            },
                Cancel: function(){
                     $(this).dialog('destroy');
            },
                Save: function(){
                    var inner_viewmanager = action_manager.inner_viewmanager;
                    inner_viewmanager.views[inner_viewmanager.active_view].controller.do_save()
                    .then(function() {
                        self.dialog.stop();
                        window.location.reload();
                    });
                }
            }
        });
       this.dialog.start().open();
       action_manager.appendTo(this.dialog);
       action_manager.render(this.dialog);
    },

    change_password :function() {
        var self = this;
        this.dialog = new openerp.web.Dialog(this,{
            modal : true,
            title : 'Change Password',
            width : 'auto',
            height : 'auto'
        });
        this.dialog.start().open();
        this.dialog.$element.html(QWeb.render("Change_Pwd", self));
        this.dialog.$element.find("form[name=change_password_form]").validate({
            submitHandler: function (form) {
                self.rpc("/web/session/change_password",{
                    'fields': $(form).serializeArray()
                }, function(result) {
                    if (result.error) {
                        self.display_error(result);
                        return;
                    } else {
                        self.session.logout();
                    }
                });
            }
        });
    },
    display_error: function (error) {
        return $('<div>').dialog({
            modal: true,
            title: error.title,
            buttons: {
                Ok: function() {
                    $(this).dialog("close");
                }
            }
        }).html(error.error);
    },
    on_logout: function() {
    }
});

openerp.web.Menu =  openerp.web.Widget.extend(/** @lends openerp.web.Menu# */{
    /**
     * @constructs openerp.web.Menu
     * @extends openerp.web.Widget
     *
     * @param parent
     * @param element_id
     * @param secondary_menu_id
     */
    init: function(parent, element_id, secondary_menu_id) {
        this._super(parent, element_id);
        this.secondary_menu_id = secondary_menu_id;
        this.$secondary_menu = $("#" + secondary_menu_id).hide();
        this.menu = false;
        this.folded = false;
        if (window.localStorage) {
            this.folded = localStorage.getItem('oe_menu_folded') === 'true';
        }
        this.float_timeout = 700;
    },
    start: function() {
        this.$secondary_menu.addClass(this.folded ? 'oe_folded' : 'oe_unfolded');
    },
    do_reload: function() {
        this.rpc("/web/menu/load", {}, this.on_loaded);
    },
    on_loaded: function(data) {
        this.data = data;
        this.$element.html(QWeb.render("Menu", { widget : this }));
        this.$secondary_menu.html(QWeb.render("Menu.secondary", { widget : this }));
        this.$element.add(this.$secondary_menu).find("a").click(this.on_menu_click);
        this.$secondary_menu.find('.oe_toggle_secondary_menu').click(this.on_toggle_fold);
    },
    on_toggle_fold: function() {
        this.$secondary_menu.toggleClass('oe_folded').toggleClass('oe_unfolded');
        if (this.folded) {
            this.$secondary_menu.find('.oe_secondary_menu.active').show();
        } else {
            this.$secondary_menu.find('.oe_secondary_menu').hide();
        }
        this.folded = !this.folded;
        if (window.localStorage) {
            localStorage.setItem('oe_menu_folded', this.folded.toString());
        }
    },
    on_menu_click: function(ev, id) {
        id = id || 0;
        var $clicked_menu, manual = false;

        if (id) {
            // We can manually activate a menu with it's id (for hash url mapping)
            manual = true;
            $clicked_menu = this.$element.find('a[data-menu=' + id + ']');
            if (!$clicked_menu.length) {
                $clicked_menu = this.$secondary_menu.find('a[data-menu=' + id + ']');
            }
        } else {
            $clicked_menu = $(ev.currentTarget);
            id = $clicked_menu.data('menu');
        }

        if (this.do_menu_click($clicked_menu, manual) && id) {
            this.session.active_id = id;
            this.rpc('/web/menu/action', {'menu_id': id}, this.on_menu_action_loaded);
        }
        if (ev) {
            ev.stopPropagation();
        }
        return false;
    },
    do_menu_click: function($clicked_menu, manual) {
        var $sub_menu, $main_menu,
            active = $clicked_menu.is('.active'),
            sub_menu_visible = false;

        if (this.$secondary_menu.has($clicked_menu).length) {
            $sub_menu = $clicked_menu.parents('.oe_secondary_menu');
            $main_menu = this.$element.find('a[data-menu=' + $sub_menu.data('menu-parent') + ']');
        } else {
            $sub_menu = this.$secondary_menu.find('.oe_secondary_menu[data-menu-parent=' + $clicked_menu.attr('data-menu') + ']');
            $main_menu = $clicked_menu;
        }

        sub_menu_visible = $sub_menu.is(':visible');
        this.$secondary_menu.find('.oe_secondary_menu').hide();

        $('.active', this.$element.add(this.$secondary_menu.show())).removeClass('active');
        $main_menu.add($clicked_menu).add($sub_menu).addClass('active');

        if (!(this.folded && manual)) {
            this.do_show_secondary($sub_menu, $main_menu);
        }

        if ($main_menu != $clicked_menu) {
            if ($clicked_menu.is('.submenu')) {
                $sub_menu.find('.submenu.opened').each(function() {
                    if (!$(this).next().has($clicked_menu).length && !$(this).is($clicked_menu)) {
                        $(this).removeClass('opened').next().hide();
                    }
                });
                $clicked_menu.toggleClass('opened').next().toggle();
            } else if ($clicked_menu.is('.leaf')) {
                $sub_menu.toggle(!this.folded);
                return true;
            }
        } else if (this.folded) {
            if (active && sub_menu_visible) {
                $sub_menu.hide();
                return true;
            }
            return manual;
        } else {
            return true;
        }
        return false;
    },
    do_show_secondary: function($sub_menu, $main_menu) {
        var self = this;
        if (this.folded) {
            var css = $main_menu.position(),
                fold_width = this.$secondary_menu.width() + 2,
                window_width = $(window).width();
            css.top += 33;
            css.left -= Math.round(($sub_menu.width() - $main_menu.width()) / 2);
            css.left = css.left < fold_width ? fold_width : css.left;
            if ((css.left + $sub_menu.width()) > window_width) {
                delete(css.left);
                css.right = 1;
            }
            $sub_menu.css(css);
            $sub_menu.mouseenter(function() {
                clearTimeout($sub_menu.data('timeoutId'));
            }).mouseleave(function(evt) {
                var timeoutId = setTimeout(function() {
                    if (self.folded) {
                        $sub_menu.hide();
                    }
                }, self.float_timeout);
                $sub_menu.data('timeoutId', timeoutId);
            });
        }
        $sub_menu.show();
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

openerp.web.WebClient = openerp.web.Widget.extend(/** @lends openerp.web.WebClient */{
    /**
     * @constructs openerp.web.WebClient
     * @extends openerp.web.Widget
     *
     * @param element_id
     */
    init: function(element_id) {
        this._super(null, element_id);
        openerp.webclient = this;

        QWeb.add_template("/web/static/src/xml/base.xml");
        var params = {};
        if(jQuery.param != undefined && jQuery.deparam(jQuery.param.querystring()).kitten != undefined) {
            this.$element.addClass("kitten-mode-activated");
        }
        this.$element.html(QWeb.render("Interface", params));

        this.notification = new openerp.web.Notification();
        this.session = new openerp.web.Session();
        this.loading = new openerp.web.Loading(this,"oe_loading");
        this.crashmanager =  new openerp.web.CrashManager(this);
        this.crashmanager.start();

        this.header = new openerp.web.Header(this);
        this.login = new openerp.web.Login(this);
        this.header.on_logout.add(this.login.on_logout);
        this.header.on_action.add(this.on_menu_action);

        this.session.on_session_invalid.add(this.login.do_ask_login);
        this.session.on_session_valid.add_last(this.header.do_update);
        this.session.on_session_invalid.add_last(this.header.do_update);
        this.session.on_session_valid.add_last(this.on_logged);

        this.menu = new openerp.web.Menu(this, "oe_menu", "oe_secondary_menu");
        this.menu.on_action.add(this.on_menu_action);

        this.url_internal_hashchange = false;
        this.url_external_hashchange = false;
        jQuery(window).bind('hashchange', this.on_url_hashchange);

    },
    start: function() {
        this._super.apply(this, arguments);
        this.notification.prependTo(this.$element);
        this.header.appendTo($("#oe_header"));
        this.session.start();
        this.login.appendTo($('#oe_login'));
        this.menu.start();
    },
    do_reload: function() {
        this.session.session_restore();
        this.menu.do_reload();
    },
    do_notify: function() {
        var n = this.notification;
        n.notify.apply(n, arguments);
    },
    do_warn: function() {
        var n = this.notification;
        n.warn.apply(n, arguments);
    },
    on_logged: function() {
        this.menu.do_reload();
        if(this.action_manager)
            this.action_manager.stop();
        this.action_manager = new openerp.web.ActionManager(this);
        this.action_manager.appendTo($("#oe_app"));
        this.action_manager.do_url_set_hash.add_last(this.do_url_set_hash);

        // if using saved actions, load the action and give it to action manager
        var parameters = jQuery.deparam(jQuery.param.querystring());
        if (parameters["s_action"] != undefined) {
            var key = parseInt(parameters["s_action"], 10);
            var self = this;
            this.rpc("/web/session/get_session_action", {key:key}, function(action) {
                self.action_manager.do_action(action);
            });
        } else if (openerp._modules_loaded) { // TODO: find better option than this
            this.load_url_state()
        } else {
            this.session.on_modules_loaded.add({
                callback: $.proxy(this, 'load_url_state'),
                unique: true,
                position: 'last'
            })
        }
    },
    /**
     * Loads state from URL if any, or checks if there is a home action and
     * loads that, assuming we're at the index
     */
    load_url_state: function () {
        var self = this;
        // TODO: add actual loading if there is url state to unpack, test on window.location.hash
        // not logged in
        if (!this.session.uid) { return; }
        var ds = new openerp.web.DataSetSearch(this, 'res.users');
        ds.read_ids([this.session.uid], ['action_id'], function (users) {
            var home_action = users[0].action_id;
            if (!home_action) {
                self.default_home();
                return;
            }
            self.execute_home_action(home_action[0], ds);
        })
    },
    default_home: function () {
    },
    /**
     * Bundles the execution of the home action
     *
     * @param {Number} action action id
     * @param {openerp.web.DataSet} dataset action executor
     */
    execute_home_action: function (action, dataset) {
        var self = this;
        this.rpc('/web/action/load', {
            action_id: action,
            context: dataset.get_context()
        }, function (meh) {
            var action = meh.result;
            action.context = _.extend(action.context || {}, {
                active_id: false,
                active_ids: [false],
                active_model: dataset.model
            });
            self.action_manager.do_action(action);
        });
    },
    do_url_set_hash: function(url) {
        if(!this.url_external_hashchange) {
            this.url_internal_hashchange = true;
            jQuery.bbq.pushState(url);
        }
    },
    on_url_hashchange: function() {
        if(this.url_internal_hashchange) {
            this.url_internal_hashchange = false;
        } else {
            var url = jQuery.deparam.fragment();
            this.url_external_hashchange = true;
            this.action_manager.on_url_hashchange(url);
            this.url_external_hashchange = false;
        }
    },
    on_menu_action: function(action) {
        this.action_manager.do_action(action);
    },
    do_about: function() {
    },

});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
