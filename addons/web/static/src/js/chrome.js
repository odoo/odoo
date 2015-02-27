/*---------------------------------------------------------
 * OpenERP Web chrome
 *---------------------------------------------------------*/
(function() {

var instance = openerp;
openerp.web.chrome = {};

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
        this.$el.notify({
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
        return this.$el.notify('create', {
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
        return this.$el.notify('create', 'oe_notification_alert', {
            title: title,
            text: text
        }, opts);
    }
});

var opened_modal = [];

instance.web.action_notify = function(element, action) {
    element.do_notify(action.params.title, action.params.text, action.params.sticky);
};
instance.web.client_actions.add("action_notify", "instance.web.action_notify");

instance.web.action_warn = function(element, action) {
    element.do_warn(action.params.title, action.params.text, action.params.sticky);
};
instance.web.client_actions.add("action_warn", "instance.web.action_warn");

/**
    A useful class to handle dialogs.

    Attributes:
    - $buttons: A jQuery element targeting a dom part where buttons can be added. It always exists
    during the lifecycle of the dialog.
*/
instance.web.Dialog = instance.web.Widget.extend({
    dialog_title: "",
    /**
        Constructor.

        @param {Widget} parent
        @param {dictionary} options A dictionary that will be forwarded to jQueryUI Dialog. Additionaly, that
            dictionary can contain the following keys:
            - size: one of the following: 'large', 'medium', 'small'
            - dialogClass: class to add to the body of dialog
            - buttons: Deprecated. The buttons key is not propagated to jQueryUI Dialog. It must be a dictionary (key = button
                label, value = click handler) or a list of dictionaries (each element in the dictionary is send to the
                corresponding method of a jQuery element targeting the <button> tag). It is deprecated because all dialogs
                in OpenERP must be personalized in some way (button in red, link instead of button, ...) and this
                feature does not allow that kind of personalization.
            - destroy_on_close: Default true. If true and the dialog is closed, it is automatically destroyed.
        @param {jQuery object} content Some content to replace this.$el .
    */
    init: function (parent, options, content) {
        var self = this;
        this._super(parent);
        this.content_to_set = content;
        this.dialog_options = {
            destroy_on_close: true,
            size: 'large', //'medium', 'small'
            buttons: null,
        };
        if (options) {
            _.extend(this.dialog_options, options);
        }
        this.on("closing", this, this._closing);
        this.$buttons = $('<div class="modal-footer"><span class="oe_dialog_custom_buttons"/></div>');
    },
    renderElement: function() {
        if (this.content_to_set) {
            this.setElement(this.content_to_set);
        } else if (this.template) {
            this._super();
        }
    },
    /**
        Opens the popup. Inits the dialog if it is not already inited.

        @return this
    */
    open: function() {
        if (!this.dialog_inited) {
            this.init_dialog();
        }
        this.$buttons.insertAfter(this.$dialog_box.find(".modal-body"));
        $('.tooltip').remove(); //remove open tooltip if any to prevent them staying when modal is opened
        //add to list of currently opened modal
        opened_modal.push(this.$dialog_box);
        return this;
    },
    _add_buttons: function(buttons) {
        var self = this;
        var $customButons = this.$buttons.find('.oe_dialog_custom_buttons').empty();
        _.each(buttons, function(fn, text) {
            // buttons can be object or array
            var oe_link_class = fn.oe_link_class;
            if (!_.isFunction(fn)) {
                text = fn.text;
                fn = fn.click;
            }
            var $but = $(QWeb.render('WidgetButton', { widget : { string: text, node: { attrs: {'class': oe_link_class} }}}));
            $customButons.append($but);
            $but.on('click', function(ev) {
                fn.call(self.$el, ev);
            });
        });
    },
    /**
        Initializes the popup.

        @return The result returned by start().
    */
    init_dialog: function() {
        var self = this;
        var options = _.extend({}, this.dialog_options);
        options.title = options.title || this.dialog_title;
        if (options.buttons) {
            this._add_buttons(options.buttons);
            delete(options.buttons);
        }
        this.renderElement();

        this.$dialog_box = $(QWeb.render('Dialog', options)).appendTo("body");
        this.$el.modal({
            'backdrop': false,
            'keyboard': true,
        });
        if (options.size !== 'large'){
            var dialog_class_size = this.$dialog_box.find('.modal-lg').removeClass('modal-lg');
            if (options.size === 'small'){
                dialog_class_size.addClass('modal-sm');
            }
        }

        this.$el.appendTo(this.$dialog_box.find(".modal-body"));
        var $dialog_content = this.$dialog_box.find('.modal-content');
        if (options.dialogClass){
            $dialog_content.find(".modal-body").addClass(options.dialogClass);
        }
        $dialog_content.openerpClass();

        this.$dialog_box.on('hidden.bs.modal', this, function() {
            self.close();
        });
        this.$dialog_box.modal('show');

        this.dialog_inited = true;
        var res = this.start();
        return res;
    },
    /**
        Closes (hide) the popup, if destroy_on_close was passed to the constructor, it will be destroyed instead.
    */
    close: function(reason) {
        if (this.dialog_inited && !this.__tmp_dialog_hiding) {
            $('.tooltip').remove(); //remove open tooltip if any to prevent them staying when modal has disappeared
            if (this.$el.is(":data(bs.modal)")) {     // may have been destroyed by closing signal
                this.__tmp_dialog_hiding = true;
                this.$dialog_box.modal('hide');
                this.__tmp_dialog_hiding = undefined;
            }
            this.trigger("closing", reason);
        }
    },
    _closing: function() {
        if (this.__tmp_dialog_destroying)
            return;
        if (this.dialog_options.destroy_on_close) {
            this.__tmp_dialog_closing = true;
            this.destroy();
            this.__tmp_dialog_closing = undefined;
        }
    },
    /**
        Destroys the popup, also closes it.
    */
    destroy: function (reason) {
        this.$buttons.remove();
        var self = this;
        _.each(this.getChildren(), function(el) {
            el.destroy();
        });
        if (! this.__tmp_dialog_closing) {
            this.__tmp_dialog_destroying = true;
            this.close(reason);
            this.__tmp_dialog_destroying = undefined;
        }
        if (this.dialog_inited && !this.isDestroyed() && this.$el.is(":data(bs.modal)")) {
            //we need this to put the instruction to remove modal from DOM at the end
            //of the queue, otherwise it might already have been removed before the modal-backdrop
            //is removed when pressing escape key
            var $element = this.$dialog_box;
            setTimeout(function () {
                //remove modal from list of opened modal since we just destroy it
                var modal_list_index = $.inArray($element, opened_modal);
                if (modal_list_index > -1){
                    opened_modal.splice(modal_list_index,1)[0].remove();
                }
                if (opened_modal.length > 0){
                    //we still have other opened modal so we should focus it
                    opened_modal[opened_modal.length-1].focus();
                    //keep class modal-open (deleted by bootstrap hide fnct) on body 
                    //to allow scrolling inside the modal
                    $('body').addClass('modal-open');
                }
            },0);
        }
        this._super();
    }
});

instance.web.CrashManager = instance.web.Class.extend({
    init: function() {
        this.active = true;
    },

    rpc_error: function(error) {
        if (!this.active) {
            return;
        }
        var handler = instance.web.crash_manager_registry.get_object(error.data.name, true);
        if (handler) {
            new (handler)(this, error).display();
            return;
        }
        if (error.data.name === "openerp.http.SessionExpiredException" || error.data.name === "werkzeug.exceptions.Forbidden") {
            this.show_warning({type: "Session Expired", data: { message: _t("Your Odoo session expired. Please refresh the current web page.") }});
            return;
        }
        if (error.data.exception_type === "except_osv" || error.data.exception_type === "warning" || error.data.exception_type === "access_error") {
            this.show_warning(error);
        } else {
            this.show_error(error);
        }
    },
    show_warning: function(error) {
        if (!this.active) {
            return;
        }
        if (error.data.exception_type === "except_osv") {
            error = _.extend({}, error, {data: _.extend({}, error.data, {message: error.data.arguments[0] + "\n\n" + error.data.arguments[1]})});
        }
        new instance.web.Dialog(this, {
            size: 'medium',
            title: "Odoo " + (_.str.capitalize(error.type) || "Warning"),
            buttons: [
                {text: _t("Ok"), click: function() { this.parents('.modal').modal('hide'); }}
            ],
        }, $('<div>' + QWeb.render('CrashManager.warning', {error: error}) + '</div>')).open();
    },
    show_error: function(error) {
        if (!this.active) {
            return;
        }
        var buttons = {};
        buttons[_t("Ok")] = function() {
            this.parents('.modal').modal('hide');
        };
        new instance.web.Dialog(this, {
            title: "Odoo " + _.str.capitalize(error.type),
            buttons: buttons
        }, QWeb.render('CrashManager.error', {session: instance.session, error: error})).open();
    },
    show_message: function(exception) {
        this.show_error({
            type: _t("Client Error"),
            message: exception,
            data: {debug: ""}
        });
    },
});

/**
    An interface to implement to handle exceptions. Register implementation in instance.web.crash_manager_registry.
*/
instance.web.ExceptionHandler = {
    /**
        @param parent The parent.
        @param error The error object as returned by the JSON-RPC implementation.
    */
    init: function(parent, error) {},
    /**
        Called to inform to display the widget, if necessary. A typical way would be to implement
        this interface in a class extending instance.web.Dialog and simply display the dialog in this
        method.
    */
    display: function() {},
};

/**
    The registry to handle exceptions. It associate a fully qualified python exception name with a class implementing
    instance.web.ExceptionHandler.
*/
instance.web.crash_manager_registry = new instance.web.Registry();

/**
 * Handle redirection warnings, which behave more or less like a regular
 * warning, with an additional redirection button.
 */
instance.web.RedirectWarningHandler = instance.web.Dialog.extend(instance.web.ExceptionHandler, {
    init: function(parent, error) {
        this._super(parent);
        this.error = error;
    },
    display: function() {
        var self = this;
        error = this.error;
        error.data.message = error.data.arguments[0];

        new instance.web.Dialog(this, {
            size: 'medium',
            title: "Odoo " + (_.str.capitalize(error.type) || "Warning"),
            buttons: [
                {text: _t("Ok"), click: function() { self.$el.parents('.modal').modal('hide');  self.destroy();}},
                {text: error.data.arguments[2],
                 oe_link_class: 'oe_link',
                 click: function() {
                    window.location.href='#action='+error.data.arguments[1];
                    self.destroy();
                }}
            ],
        }, QWeb.render('CrashManager.warning', {error: error})).open();
    }
});
instance.web.crash_manager_registry.add('openerp.exceptions.RedirectWarning', 'instance.web.RedirectWarningHandler');

instance.web.Loading = instance.web.Widget.extend({
    template: _t("Loading"),
    init: function(parent) {
        this._super(parent);
        this.count = 0;
        this.blocked_ui = false;
        this.session.on("request", this, this.request_call);
        this.session.on("response", this, this.response_call);
        this.session.on("response_failed", this, this.response_call);
    },
    destroy: function() {
        this.on_rpc_event(-this.count);
        this._super();
    },
    request_call: function() {
        this.on_rpc_event(1);
    },
    response_call: function() {
        this.on_rpc_event(-1);
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
                this.$el.text(_.str.sprintf( _t("Loading (%d)"), this.count));
            } else {
                this.$el.text(_t("Loading"));
            }
            this.$el.show();
            this.getParent().$el.addClass('oe_wait');
        } else {
            this.count = 0;
            clearTimeout(this.long_running_timer);
            // Don't unblock if blocked by somebody else
            if (self.blocked_ui) {
                this.blocked_ui = false;
                instance.web.unblockUI();
            }
            this.$el.fadeOut();
            this.getParent().$el.removeClass('oe_wait');
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
        var fetch_db = this.rpc("/web/database/get_list", {}).then(
            function(result) {
                self.db_list = result;
            },
            function (_, ev) {
                ev.preventDefault();
                self.db_list = null;
            });
        var fetch_langs = this.rpc("/web/session/get_lang_list", {}).done(function(result) {
            self.lang_list = result;
        });
        return $.when(fetch_db, fetch_langs).always(self.do_render);
    },
    do_render: function() {
        var self = this;
        instance.webclient.toggle_bars(true);
        self.$el.html(QWeb.render("DatabaseManager", { widget : self }));
        $('.oe_user_menu_placeholder').append(QWeb.render("DatabaseManager.user_menu",{ widget : self }));
        $('.oe_secondary_menus_container').append(QWeb.render("DatabaseManager.menu",{ widget : self }));
        $('ul.oe_secondary_submenu > li:first').addClass('active');
        $('ul.oe_secondary_submenu > li').bind('click', function (event) {
            var menuitem = $(this);
            menuitem.addClass('active').siblings().removeClass('active');
            var form_id =menuitem.find('a').attr('href');
            $(form_id).show().siblings().hide();
            event.preventDefault();
        });
        $('#back-to-login').click(self.do_exit);
        self.$el.find("td").addClass("oe_form_group_cell");
        self.$el.find("tr td:first-child").addClass("oe_form_group_cell_label");
        self.$el.find("label").addClass("oe_form_label");
        self.$el.find("form[name=create_db_form]").validate({ submitHandler: self.do_create });
        self.$el.find("form[name=duplicate_db_form]").validate({ submitHandler: self.do_duplicate });
        self.$el.find("form[name=drop_db_form]").validate({ submitHandler: self.do_drop });
        self.$el.find("form[name=backup_db_form]").validate({ submitHandler: self.do_backup });
        self.$el.find("form[name=restore_db_form]").validate({ submitHandler: self.do_restore });
        self.$el.find("form[name=change_pwd_form]").validate({
            messages: {
                old_pwd: _t("Please enter your previous password"),
                new_pwd: _t("Please enter your new password"),
                confirm_pwd: {
                    required: _t("Please confirm your new password"),
                    equalTo: _t("The confirmation does not match the password")
                }
            },
            submitHandler: self.do_change_password
        });
    },
    destroy: function () {
        this.$el.find('#db-create, #db-drop, #db-backup, #db-restore, #db-change-password, #back-to-login').unbind('click').end().empty();
        this._super();
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
        return new instance.web.Dialog(this, {
            size: 'medium',
            title: error.title,
            buttons: [
                {text: _t("Ok"), click: function() { this.parents('.modal').modal('hide'); }}
            ]
        }, $('<div>').html(error.error)).open();
    },
    do_create: function(form) {
        var self = this;
        var fields = $(form).serializeArray();
        self.rpc("/web/database/create", {'fields': fields}).done(function(result) {
            if (result) {
                instance.web.redirect('/web');
            } else {
                alert("Failed to create database");
            }
        });
    },
    do_duplicate: function(form) {
        var self = this;
        var fields = $(form).serializeArray();
        self.rpc("/web/database/duplicate", {'fields': fields}).then(function(result) {
            if (result.error) {
                self.display_error(result);
                return;
            }
            self.do_notify(_t("Duplicating database"), _t("The database has been duplicated."));
            self.start();
        });
    },
    do_drop: function(form) {
        var self = this;
        var $form = $(form),
            fields = $form.serializeArray(),
            $db_list = $form.find('[name=drop_db]'),
            db = $db_list.val();
        if (!db || !confirm(_.str.sprintf(_t("Do you really want to delete the database: %s ?"), db))) {
            return;
        }
        self.rpc("/web/database/drop", {'fields': fields}).done(function(result) {
            if (result.error) {
                self.display_error(result);
                return;
            }
            self.do_notify(_t("Dropping database"), _.str.sprintf(_t("The database %s has been dropped"), db));
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
                if (error && error[1]) {
                    self.display_error(error[1][0]);
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
                        title: _t("Access Denied"),
                        error: _t("Incorrect super-administrator password")
                    });
                } else {
                    self.display_error({
                        title: _t("Restore Database"),
                        error: _t("Could not restore the database")
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
        }).done(function(result) {
            if (result.error) {
                self.display_error(result);
                return;
            }
            self.unblockUI();
            self.do_notify(_t("Changed Password"), _t("Password has been changed successfully"));
        });
    },
    do_exit: function () {
        this.$el.remove();
        instance.web.redirect('/web');
    }
});
instance.web.client_actions.add("database_manager", "instance.web.DatabaseManager");

instance.web.login = function() {
    instance.web.redirect('/web/login');
};
instance.web.client_actions.add("login", "instance.web.login");

instance.web.logout = function() {
    instance.web.redirect('/web/session/logout');
};
instance.web.client_actions.add("logout", "instance.web.logout");


/**
 * Redirect to url by replacing window.location
 * If wait is true, sleep 1s and wait for the server i.e. after a restart.
 */
instance.web.redirect = function(url, wait) {
    // Dont display a dialog if some xmlhttprequest are in progress
    if (instance.client && instance.client.crashmanager) {
        instance.client.crashmanager.active = false;
    }

    var load = function() {
        var old = "" + window.location;
        var old_no_hash = old.split("#")[0];
        var url_no_hash = url.split("#")[0];
        location.assign(url);
        if (old_no_hash === url_no_hash) {
            location.reload(true);
        }
    };

    var wait_server = function() {
        instance.session.rpc("/web/webclient/version_info", {}).done(load).fail(function() {
            setTimeout(wait_server, 250);
        });
    };

    if (wait) {
        setTimeout(wait_server, 1000);
    } else {
        load();
    }
};

/**
 * Client action to reload the whole interface.
 * If params.menu_id, it opens the given menu entry.
 * If params.wait, reload will wait the openerp server to be reachable before reloading
 */
instance.web.Reload = function(parent, action) {
    var params = action.params || {};
    var menu_id = params.menu_id || false;
    var l = window.location;

    var sobj = $.deparam(l.search.substr(1));
    if (params.url_search) {
        sobj = _.extend(sobj, params.url_search);
    }
    var search = '?' + $.param(sobj);

    var hash = l.hash;
    if (menu_id) {
        hash = "#menu_id=" + menu_id;
    }
    var url = l.protocol + "//" + l.host + l.pathname + search + hash;

    instance.web.redirect(url, params.wait);
};
instance.web.client_actions.add("reload", "instance.web.Reload");

/**
 * Client action to refresh the session context (making sure
 * HTTP requests will have the right one) then reload the
 * whole interface.
 */
instance.web.ReloadContext = function(parent, action) {
    // side-effect of get_session_info is to refresh the session context
    instance.session.rpc("/web/session/get_session_info", {}).then(function() {
        instance.web.Reload(parent, action);
    });
}
instance.web.client_actions.add("reload_context", "instance.web.ReloadContext");

/**
 * Client action to go back in breadcrumb history.
 * If can't go back in history stack, will go back to home.
 */
instance.web.HistoryBack = function(parent) {
    if (!parent.history_back()) {
        instance.web.Home(parent);
    }
};
instance.web.client_actions.add("history_back", "instance.web.HistoryBack");

/**
 * Client action to go back home.
 */
instance.web.Home = function(parent, action) {
    var url = '/' + (window.location.search || '');
    instance.web.redirect(url, action && action.params && action.params.wait);
};
instance.web.client_actions.add("home", "instance.web.Home");

instance.web.ChangePassword =  instance.web.Widget.extend({
    template: "ChangePassword",
    start: function() {
        var self = this;
        this.getParent().dialog_title = _t("Change Password");
        var $button = self.$el.find('.oe_form_button');
        $button.appendTo(this.getParent().$buttons);
        $button.eq(2).click(function(){
           self.$el.parents('.modal').modal('hide');
        });
        $button.eq(0).click(function(){
          self.rpc("/web/session/change_password",{
               'fields': $("form[name=change_password_form]").serializeArray()
          }).done(function(result) {
               if (result.error) {
                  self.display_error(result);
                  return;
               } else {
                   instance.webclient.on_logout();
               }
          });
       });
    },
    display_error: function (error) {
        return new instance.web.Dialog(this, {
            size: 'medium',
            title: error.title,
            buttons: [
                {text: _t("Ok"), click: function() { this.parents('.modal').modal('hide'); }}
            ]
        }, $('<div>').html(error.error)).open();
    },
});
instance.web.client_actions.add("change_password", "instance.web.ChangePassword");

instance.web.Menu =  instance.web.Widget.extend({
    init: function() {
        var self = this;
        this._super.apply(this, arguments);
        this.is_bound = $.Deferred();
        this.maximum_visible_links = 'auto'; // # of menu to show. 0 = do not crop, 'auto' = algo
        this.data = {data:{children:[]}};
        this.on("menu_bound", this, function() {
            // launch the fetch of needaction counters, asynchronous
            var $all_menus = self.$el.parents('body').find('.oe_webclient').find('[data-menu]');
            var all_menu_ids = _.map($all_menus, function (menu) {return parseInt($(menu).attr('data-menu'), 10);});
            if (!_.isEmpty(all_menu_ids)) {
                this.do_load_needaction(all_menu_ids);
            }
        });
    },
    start: function() {
        this._super.apply(this, arguments);
        return this.bind_menu();
    },
    do_reload: function() {
        var self = this;
        self.bind_menu();
    },
    bind_menu: function() {
        var self = this;
        this.$secondary_menus = this.$el.parents().find('.oe_secondary_menus_container')
        this.$secondary_menus.on('click', 'a[data-menu]', this.on_menu_click);
        this.$el.on('click', 'a[data-menu]', this.on_top_menu_click);
        // Hide second level submenus
        this.$secondary_menus.find('.oe_menu_toggler').siblings('.oe_secondary_submenu').hide();
        if (self.current_menu) {
            self.open_menu(self.current_menu);
        }
        this.trigger('menu_bound');

        var lazyreflow = _.debounce(this.reflow.bind(this), 200);
        instance.web.bus.on('resize', this, function() {
            if (parseInt(self.$el.parent().css('width')) <= 768 ) {
                lazyreflow('all_outside');
            } else {
                lazyreflow();
            }
        });
        instance.web.bus.trigger('resize');

        this.is_bound.resolve();
    },
    do_load_needaction: function (menu_ids) {
        var self = this;
        menu_ids = _.compact(menu_ids);
        if (_.isEmpty(menu_ids)) {
            return $.when();
        }
        return this.rpc("/web/menu/load_needaction", {'menu_ids': menu_ids}).done(function(r) {
            self.on_needaction_loaded(r);
        });
    },
    on_needaction_loaded: function(data) {
        var self = this;
        this.needaction_data = data;
        _.each(this.needaction_data, function (item, menu_id) {
            var $item = self.$secondary_menus.find('a[data-menu="' + menu_id + '"]');
            $item.find('.badge').remove();
            if (item.needaction_counter && item.needaction_counter > 0) {
                $item.append(QWeb.render("Menu.needaction_counter", { widget : item }));
            }
        });
    },
    /**
     * Reflow the menu items and dock overflowing items into a "More" menu item.
     * Automatically called when 'menu_bound' event is triggered and on window resizing.
     *
     * @param {string} behavior If set to 'all_outside', all the items are displayed. If set to
     * 'all_inside', all the items are hidden under the more item. If not set, only the 
     * overflowing items are hidden.
     */
    reflow: function(behavior) {
        var self = this;
        var $more_container = this.$('#menu_more_container').hide();
        var $more = this.$('#menu_more');
        var $systray = this.$el.parents().find('.oe_systray');

        $more.children('li').insertBefore($more_container);  // Pull all the items out of the more menu
        
        // 'all_outside' beahavior should display all the items, so hide the more menu and exit
        if (behavior === 'all_outside') {
            this.$el.find('li').show();
            $more_container.hide();
            return;
        }

        var $toplevel_items = this.$el.find('li').not($more_container).not($systray.find('li')).hide();
        $toplevel_items.each(function() {
            // In all inside mode, we do not compute to know if we must hide the items, we hide them all
            if (behavior === 'all_inside') {
                return false;
            }
            var remaining_space = self.$el.parent().width() - $more_container.outerWidth();
            self.$el.parent().children(':visible').each(function() {
                remaining_space -= $(this).outerWidth();
            });

            if ($(this).width() > remaining_space) {
                return false;
            }
            $(this).show();
        });
        $more.append($toplevel_items.filter(':hidden').show());
        $more_container.toggle(!!$more.children().length || behavior === 'all_inside');
        // Hide toplevel item if there is only one
        var $toplevel = this.$el.children("li:visible");
        if ($toplevel.length === 1 && behavior != 'all_inside') {
            $toplevel.hide();
        }
    },
    /**
     * Opens a given menu by id, as if a user had browsed to that menu by hand
     * except does not trigger any event on the way
     *
     * @param {Number} id database id of the terminal menu to select
     */
    open_menu: function (id) {
        this.current_menu = id;
        this.session.active_id = id;
        var $clicked_menu, $sub_menu, $main_menu;
        $clicked_menu = this.$el.add(this.$secondary_menus).find('a[data-menu=' + id + ']');
        this.trigger('open_menu', id, $clicked_menu);

        if (this.$secondary_menus.has($clicked_menu).length) {
            $sub_menu = $clicked_menu.parents('.oe_secondary_menu');
            $main_menu = this.$el.find('a[data-menu=' + $sub_menu.data('menu-parent') + ']');
        } else {
            $sub_menu = this.$secondary_menus.find('.oe_secondary_menu[data-menu-parent=' + $clicked_menu.attr('data-menu') + ']');
            $main_menu = $clicked_menu;
        }

        // Activate current main menu
        this.$el.find('.active').removeClass('active');
        $main_menu.parent().addClass('active');

        // Show current sub menu
        this.$secondary_menus.find('.oe_secondary_menu').hide();
        $sub_menu.show();

        // Hide/Show the leftbar menu depending of the presence of sub-items
        this.$secondary_menus.parent('.oe_leftbar').toggle(!!$sub_menu.children().length);

        // Activate current menu item and show parents
        this.$secondary_menus.find('.active').removeClass('active');
        if ($main_menu !== $clicked_menu) {
            $clicked_menu.parents().show();
            if ($clicked_menu.is('.oe_menu_toggler')) {
                $clicked_menu.toggleClass('oe_menu_opened').siblings('.oe_secondary_submenu:first').toggle();
            } else {
                $clicked_menu.parent().addClass('active');
            }
        }
        // add a tooltip to cropped menu items
        this.$secondary_menus.find('.oe_secondary_submenu li a span').each(function() {
            $(this).tooltip(this.scrollWidth > this.clientWidth ? {title: $(this).text().trim(), placement: 'right'} :'destroy');
       });
    },
    /**
     * Call open_menu with the first menu_item matching an action_id
     *
     * @param {Number} id the action_id to match
     */
    open_action: function (id) {
        var $menu = this.$el.add(this.$secondary_menus).find('a[data-action-id="' + id + '"]');
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
        var $item = this.$el.find('a[data-menu=' + id + ']');
        if (!$item.length) {
            $item = this.$secondary_menus.find('a[data-menu=' + id + ']');
        }
        var action_id = $item.data('action-id');
        // If first level menu doesnt have action trigger first leaf
        if (!action_id) {
            if(this.$el.has($item).length) {
                var $sub_menu = this.$secondary_menus.find('.oe_secondary_menu[data-menu-parent=' + id + ']');
                var $items = $sub_menu.find('a[data-action-id]').filter('[data-action-id!=""]');
                if($items.length) {
                    action_id = $items.data('action-id');
                    id = $items.data('menu');
                }
            }
        }
        if (action_id) {
            this.trigger('menu_click', {
                action_id: action_id,
                needaction: needaction,
                id: id,
                previous_menu_id: this.current_menu // Here we don't know if action will fail (in which case we have to revert menu)
            }, $item);
        } else {
            console.log('Menu no action found web test 04 will fail');
        }
        this.open_menu(id);
    },
    do_reload_needaction: function () {
        var self = this;
        if (self.current_menu) {
            self.do_load_needaction([self.current_menu]).then(function () {
                self.trigger("need_action_reloaded");
            });
        }
    },
    /**
     * Jquery event handler for menu click
     *
     * @param {Event} ev the jquery event
     */
    on_top_menu_click: function(ev) {
        ev.preventDefault();
        var self = this;
        var id = $(ev.currentTarget).data('menu');

        // Fetch the menu leaves ids in order to check if they need a 'needaction'
        var $secondary_menu = this.$el.parents().find('.oe_secondary_menu[data-menu-parent=' + id + ']');
        var $menu_leaves = $secondary_menu.children().find('.oe_menu_leaf');
        var menu_ids = _.map($menu_leaves, function (leave) {return parseInt($(leave).attr('data-menu'), 10);});

        self.do_load_needaction(menu_ids).then(function () {
            self.trigger("need_action_reloaded");
        });
        this.$el.parents().find(".oe_secondary_menus_container").scrollTop(0,0);

        this.on_menu_click(ev);
    },
    on_menu_click: function(ev) {
        ev.preventDefault();
        var needaction = $(ev.target).is('div#menu_counter');
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
        this.$el.on('click', '.dropdown-menu li a[data-menu]', function(ev) {
            ev.preventDefault();
            var f = self['on_menu_' + $(this).data('menu')];
            if (f) {
                f($(this));
            }
        });
        this.$el.parent().show()
    },
    do_update: function () {
        var self = this;
        var fct = function() {
            var $avatar = self.$el.find('.oe_topbar_avatar');
            $avatar.attr('src', $avatar.data('default-src'));
            if (!self.session.uid)
                return;
            var func = new instance.web.Model("res.users").get_func("read");
            return self.alive(func(self.session.uid, ["name", "company_id"])).then(function(res) {
                var topbar_name = res.name;
                if(instance.session.debug)
                    topbar_name = _.str.sprintf("%s (%s)", topbar_name, instance.session.db);
                if(res.company_id[0] > 1)
                    topbar_name = _.str.sprintf("%s (%s)", topbar_name, res.company_id[1]);
                self.$el.find('.oe_topbar_name').text(topbar_name);
                if (!instance.session.debug) {
                    topbar_name = _.str.sprintf("%s (%s)", topbar_name, instance.session.db);
                }
                var avatar_src = self.session.url('/web/binary/image', {model:'res.users', field: 'image_small', id: self.session.uid});
                $avatar.attr('src', avatar_src);

                openerp.web.bus.trigger('resize');  // Re-trigger the reflow logic
            });
        };
        this.update_promise = this.update_promise.then(fct, fct);
    },
    on_menu_help: function() {
        window.open('http://help.odoo.com', '_blank');
    },
    on_menu_logout: function() {
        this.trigger('user_logout');
    },
    on_menu_settings: function() {
        var self = this;
        if (!this.getParent().has_uncommitted_changes()) {
            self.rpc("/web/action/load", { action_id: "base.action_res_users_my" }).done(function(result) {
                result.res_id = instance.session.uid;
                self.getParent().action_manager.do_action(result);
            });
        }
    },
    on_menu_account: function() {
        var self = this;
        if (!this.getParent().has_uncommitted_changes()) {
            var P = new instance.web.Model('ir.config_parameter');
            P.call('get_param', ['database.uuid']).then(function(dbuuid) {
                var state = {
                            'd': instance.session.db,
                            'u': window.location.protocol + '//' + window.location.host,
                        };
                var params = {
                    response_type: 'token',
                    client_id: dbuuid || '',
                    state: JSON.stringify(state),
                    scope: 'userinfo',
                };
                instance.web.redirect('https://accounts.odoo.com/oauth2/auth?'+$.param(params));
            }).fail(function(result, ev){
                ev.preventDefault();
                instance.web.redirect('https://accounts.odoo.com/web');
            });
        }
    },
    on_menu_about: function() {
        var self = this;
        self.rpc("/web/webclient/version_info", {}).done(function(res) {
            var $help = $(QWeb.render("UserMenu.about", {version_info: res}));
            $help.find('a.oe_activate_debug_mode').click(function (e) {
                e.preventDefault();
                window.location = $.param.querystring( window.location.href, 'debug');
            });
            new instance.web.Dialog(this, {
                size: 'medium',
                dialogClass: 'oe_act_window',
                title: _t("About"),
            }, $help).open();
        });
    },
});

instance.web.FullscreenWidget = instance.web.Widget.extend({
    /**
     * Widgets extending the FullscreenWidget will be displayed fullscreen,
     * and will have a fixed 1:1 zoom level on mobile devices.
     */
    start: function(){
        if(!$('#oe-fullscreenwidget-viewport').length){
            $('head').append('<meta id="oe-fullscreenwidget-viewport" name="viewport" content="initial-scale=1.0; maximum-scale=1.0; user-scalable=0;">');
        }
        instance.webclient.set_content_full_screen(true);
        return this._super();
    },
    destroy: function(){
        instance.webclient.set_content_full_screen(false);
        $('#oe-fullscreenwidget-viewport').remove();
        return this._super();
    },

});

instance.web.Client = instance.web.Widget.extend({
    init: function(parent, origin) {
        instance.client = instance.webclient = this;
        this.client_options = {};
        this._super(parent);
        this.origin = origin;
    },
    start: function() {
        var self = this;
        return instance.session.session_bind(this.origin).then(function() {
            self.bind_events();
            return self.show_common();
        });
    },
    bind_events: function() {
        var self = this;
        $('.oe_systray').show();
        this.$el.on('mouseenter', '.oe_systray > div:not([data-toggle=tooltip])', function() {
            $(this).attr('data-toggle', 'tooltip').tooltip().trigger('mouseenter');
        });
        this.$el.on('click', '.oe_dropdown_toggle', function(ev) {
            ev.preventDefault();
            var $toggle = $(this);
            var doc_width = $(document).width();
            var $menu = $toggle.siblings('.oe_dropdown_menu');
            $menu = $menu.size() >= 1 ? $menu : $toggle.find('.oe_dropdown_menu');
            var state = $menu.is('.oe_opened');
            setTimeout(function() {
                // Do not alter propagation
                $toggle.add($menu).toggleClass('oe_opened', !state);
                if (!state) {
                    // Move $menu if outside window's edge
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
            $('.tooltip').remove();
            if (!$(ev.target).is('input[type=file]')) {
                self.$el.find('.oe_dropdown_menu.oe_opened, .oe_dropdown_toggle.oe_opened').removeClass('oe_opened');
            }
        });
    },
    show_common: function() {
        var self = this;
        this.crashmanager =  new instance.web.CrashManager();
        instance.session.on('error', this.crashmanager, this.crashmanager.rpc_error);
        self.notification = new instance.web.Notification(this);
        self.notification.appendTo(self.$el.find('.openerp'));
        self.loading = new instance.web.Loading(self);
        self.loading.appendTo(self.$('.openerp_webclient_container'));
        self.action_manager = new instance.web.ActionManager(self);
        self.action_manager.appendTo(self.$('.oe_application'));
    },
    toggle_bars: function(value) {
        this.$('tr:has(td.navbar),.oe_leftbar').toggle(value);
    },
    has_uncommitted_changes: function() {
        return false;
    },
});

instance.web.WebClient = instance.web.Client.extend({
    init: function(parent, client_options) {
        this._super(parent);
        if (client_options) {
            _.extend(this.client_options, client_options);
        }
        this._current_state = null;
        this.menu_dm = new instance.web.DropMisordered();
        this.action_mutex = new $.Mutex();
        this.set('title_part', {"zopenerp": "Odoo"});
    },
    start: function() {
        var self = this;
        this.on("change:title_part", this, this._title_changed);
        this._title_changed();

        return $.when(this._super()).then(function() {
            if (jQuery.deparam !== undefined && jQuery.deparam(jQuery.param.querystring()).kitten !== undefined) {
                self.to_kitten();
            }
            if (self.session.session_is_valid()) {
                self.show_application();
            }
            if (self.client_options.action) {
                self.action_manager.do_action(self.client_options.action);
                delete(self.client_options.action);
            }
        });
    },
    to_kitten: function() {
        this.kitten = true;
        $("body").addClass("kitten-mode-activated");
        $("body").css("background-image", "url(" + instance.session.origin + "/web/static/src/img/back-enable.jpg" + ")");
        if ($.blockUI) {
            var imgkit = Math.floor(Math.random() * 2 + 1);
            $.blockUI.defaults.message = '<img src="/web/static/src/img/k-waiting' + imgkit + '.gif" class="loading-kitten">';
        }
    },
    /**
        Sets the first part of the title of the window, dedicated to the current action.
    */
    set_title: function(title) {
        this.set_title_part("action", title);
    },
    /**
        Sets an arbitrary part of the title of the window. Title parts are identified by strings. Each time
        a title part is changed, all parts are gathered, ordered by alphabetical order and displayed in the
        title of the window separated by '-'.
    */
    set_title_part: function(part, title) {
        var tmp = _.clone(this.get("title_part"));
        tmp[part] = title;
        this.set("title_part", tmp);
    },
    _title_changed: function() {
        var parts = _.sortBy(_.keys(this.get("title_part")), function(x) { return x; });
        var tmp = "";
        _.each(parts, function(part) {
            var str = this.get("title_part")[part];
            if (str) {
                tmp = tmp ? tmp + " - " + str : str;
            }
        }, this);
        document.title = tmp;
    },
    show_common: function() {
        var self = this;
        this._super();
        window.onerror = function (message, file, line) {
            self.crashmanager.show_error({
                type: _t("Client Error"),
                message: message,
                data: {debug: file + ':' + line}
            });
        };
    },
    show_application: function() {
        var self = this;
        self.toggle_bars(true);

        self.update_logo();
        this.$('.oe_logo_edit_admin').click(function(ev) {
            self.logo_edit(ev);
        });

        // Menu is rendered server-side thus we don't want the widget to create any dom
        self.menu = new instance.web.Menu(self);
        self.menu.setElement(this.$el.parents().find('.oe_application_menu_placeholder'));
        self.menu.start();
        self.menu.on('menu_click', this, this.on_menu_action);
        self.user_menu = new instance.web.UserMenu(self);
        self.user_menu.appendTo(this.$el.parents().find('.oe_user_menu_placeholder'));
        self.user_menu.on('user_logout', self, self.on_logout);
        self.user_menu.do_update();
        self.bind_hashchange();
        self.set_title();
        self.check_timezone();
        if (self.client_options.action_post_login) {
            self.action_manager.do_action(self.client_options.action_post_login);
            delete(self.client_options.action_post_login);
        }
    },
    update_logo: function() {
        var company = this.session.company_id;
        var img = this.session.url('/web/binary/company_logo' + '?db=' + this.session.db + (company ? '&company=' + company : ''));
        this.$('.oe_logo img').attr('src', '').attr('src', img);
        this.$('.oe_logo_edit').toggleClass('oe_logo_edit_admin', this.session.uid === 1);
    },
    logo_edit: function(ev) {
        var self = this;
        ev.preventDefault();
        self.alive(new instance.web.Model("res.users").get_func("read")(this.session.uid, ["company_id"])).then(function(res) {
            self.rpc("/web/action/load", { action_id: "base.action_res_company_form" }).done(function(result) {
                result.res_id = res['company_id'][0];
                result.target = "new";
                result.views = [[false, 'form']];
                result.flags = {
                    action_buttons: true,
                };
                self.action_manager.do_action(result);
                var form = self.action_manager.dialog_widget.views.form.controller;
                form.on("on_button_cancel", self.action_manager, self.action_manager.dialog_stop);
                form.on('record_saved', self, function() {
                    self.action_manager.dialog_stop();
                    self.update_logo();
                });
            });
        });
        return false;
    },
    check_timezone: function() {
        var self = this;
        return self.alive(new instance.web.Model('res.users').call('read', [[this.session.uid], ['tz_offset']])).then(function(result) {
            var user_offset = result[0]['tz_offset'];
            var offset = -(new Date().getTimezoneOffset());
            // _.str.sprintf()'s zero front padding is buggy with signed decimals, so doing it manually
            var browser_offset = (offset < 0) ? "-" : "+";
            browser_offset += _.str.sprintf("%02d", Math.abs(offset / 60));
            browser_offset += _.str.sprintf("%02d", Math.abs(offset % 60));
            if (browser_offset !== user_offset) {
                var $icon = $(QWeb.render('WebClient.timezone_systray'));
                $icon.on('click', function() {
                    var notification = self.do_warn(_t("Timezone Mismatch"), QWeb.render('WebClient.timezone_notification', {
                        user_timezone: instance.session.user_context.tz || 'UTC',
                        user_offset: user_offset,
                        browser_offset: browser_offset,
                    }), true);
                    notification.element.find('.oe_webclient_timezone_notification').on('click', function() {
                        notification.close();
                    }).find('a').on('click', function() {
                        notification.close();
                        self.user_menu.on_menu_settings();
                        return false;
                    });
                });
                $icon.prependTo(window.$('.oe_systray'));
            }
        });
    },
    destroy_content: function() {
        _.each(_.clone(this.getChildren()), function(el) {
            el.destroy();
        });
        this.$el.children().remove();
    },
    do_reload: function() {
        var self = this;
        return this.session.session_reload().then(function () {
            instance.session.load_modules(true).then(
                self.menu.proxy('do_reload')); });
    },
    do_notify: function() {
        var n = this.notification;
        return n.notify.apply(n, arguments);
    },
    do_warn: function() {
        var n = this.notification;
        return n.warn.apply(n, arguments);
    },
    on_logout: function() {
        var self = this;
        if (!this.has_uncommitted_changes()) {
            self.action_manager.do_action('logout');
        }
    },
    bind_hashchange: function() {
        var self = this;
        $(window).bind('hashchange', this.on_hashchange);

        var state = $.bbq.getState(true);
        if (_.isEmpty(state) || state.action == "login") {
            self.menu.is_bound.done(function() {
                new instance.web.Model("res.users").call("read", [self.session.uid, ["action_id"]]).done(function(data) {
                    if(data.action_id) {
                        self.action_manager.do_action(data.action_id[0]);
                        self.menu.open_action(data.action_id[0]);
                    } else {
                        var first_menu_id = self.menu.$el.find("a:first").data("menu");
                        if(first_menu_id) {
                            self.menu.menu_click(first_menu_id);
                        }                    }
                });
            });
        } else {
            $(window).trigger('hashchange');
        }
    },
    on_hashchange: function(event) {
        var self = this;
        var stringstate = event.getState(false);
        if (!_.isEqual(this._current_state, stringstate)) {
            var state = event.getState(true);
            if(!state.action && state.menu_id) {
                self.menu.is_bound.done(function() {
                    self.menu.menu_click(state.menu_id);
                });
            } else {
                state._push_me = false;  // no need to push state back...
                this.action_manager.do_load_state(state, !!this._current_state);
            }
        }
        this._current_state = stringstate;
    },
    do_push_state: function(state) {
        this.set_title(state.title);
        delete state.title;
        var url = '#' + $.param(state);
        this._current_state = $.deparam($.param(state), false);     // stringify all values
        $.bbq.pushState(url);
        this.trigger('state_pushed', state);
    },
    on_menu_action: function(options) {
        var self = this;
        return this.menu_dm.add(this.rpc("/web/action/load", { action_id: options.action_id }))
            .then(function (result) {
                return self.action_mutex.exec(function() {
                    if (options.needaction) {
                        result.context = new instance.web.CompoundContext(result.context, {
                            search_default_message_unread: true,
                            search_disable_custom_filters: true,
                        });
                    }
                    var completed = $.Deferred();
                    $.when(self.action_manager.do_action(result, {
                        clear_breadcrumbs: true,
                        action_menu_id: self.menu.current_menu,
                    })).fail(function() {
                        self.menu.open_menu(options.previous_menu_id);
                    }).always(function() {
                        completed.resolve();
                    });
                    setTimeout(function() {
                        completed.resolve();
                    }, 2000);
                    // We block the menu when clicking on an element until the action has correctly finished
                    // loading. If something crash, there is a 2 seconds timeout before it's unblocked.
                    return completed;
                });
            });
    },
    set_content_full_screen: function(fullscreen) {
        $(document.body).css('overflow-y', fullscreen ? 'hidden' : 'scroll');
        this.$('.oe_webclient').toggleClass(
            'oe_content_full_screen', fullscreen);
    },
    has_uncommitted_changes: function() {
        var $e = $.Event('clear_uncommitted_changes');
        instance.web.bus.trigger('clear_uncommitted_changes', $e);
        if ($e.isDefaultPrevented()) {
            return true;
        } else {
            return this._super.apply(this, arguments);
        }
    },
});

instance.web.EmbeddedClient = instance.web.Client.extend({
    _template: 'EmbedClient',
    init: function(parent, origin, dbname, login, key, action_id, options) {
        this._super(parent, origin);
        this.bind_credentials(dbname, login, key);
        this.action_id = action_id;
        this.options = options || {};
    },
    start: function() {
        var self = this;
        return $.when(this._super()).then(function() {
            return self.authenticate().then(function() {
                if (!self.action_id) {
                    return;
                }
                return self.rpc("/web/action/load", { action_id: self.action_id }).done(function(result) {
                    var action = result;
                    action.flags = _.extend({
                        //views_switcher : false,
                        search_view : false,
                        action_buttons : false,
                        sidebar : false
                        //pager : false
                    }, self.options, action.flags || {});

                    self.do_action(action);
                });
            });
        });
    },

    do_action: function(/*...*/) {
        var am = this.action_manager;
        return am.do_action.apply(am, arguments);
    },

    authenticate: function() {
        var s = instance.session;
        if (s.session_is_valid() && s.db === this.dbname && s.login === this.login) {
            return $.when();
        }
        return instance.session.session_authenticate(this.dbname, this.login, this.key);
    },

    bind_credentials: function(dbname, login, key) {
        this.dbname = dbname;
        this.login = login;
        this.key = key;
    },

});

instance.web.embed = function (origin, dbname, login, key, action, options) {
    $('head').append($('<link>', {
        'rel': 'stylesheet',
        'type': 'text/css',
        'href': origin +'/web/css/web.assets_webclient'
    }));
    var currentScript = document.currentScript;
    if (!currentScript) {
        var sc = document.getElementsByTagName('script');
        currentScript = sc[sc.length-1];
    }
    var client = new instance.web.EmbeddedClient(null, origin, dbname, login, key, action, options);
    client.insertAfter(currentScript);
};

})();

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
