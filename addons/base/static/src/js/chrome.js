/*---------------------------------------------------------
 * OpenERP base library
 *---------------------------------------------------------*/

openerp.base.chrome = function(openerp) {

openerp.base.Session = openerp.base.Widget.extend( /** @lends openerp.base.Session# */{
    /**
     * @constructs
     * @param element_id to use for exception reporting
     * @param server
     * @param port
     */
    init: function(parent, element_id, server, port) {
        this._super(parent, element_id);
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
        this.sc_list ={};
        this.active_id = "";
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
        var self = this;
        // Construct a JSON-RPC2 request, method is currently unused
        params.session_id = this.session_id;

        // Call using the rpc_mode
        var deferred = $.Deferred();
        this.rpc_ajax(url, {
            jsonrpc: "2.0",
            method: "call",
            params: params,
            id:null
        }).then(function () {deferred.resolve.apply(deferred, arguments);},
                function(error) {deferred.reject(error, $.Event());});
        return deferred.fail(function() {
            deferred.fail(function(error, event) {
                if (!event.isDefaultPrevented()) {
                    self.on_rpc_error(error, event);
                }
            });
        }).then(success_callback, error_callback).promise();
    },
    /**
     * Raw JSON-RPC call
     *
     * @returns {jQuery.Deferred} ajax-based deferred object
     */
    rpc_ajax: function(url, payload) {
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
            processData: false
        }, url);
        var deferred = $.Deferred();
        $.ajax(ajax).done(function(response, textStatus, jqXHR) {
            self.on_rpc_response();
            if (!response.error) {
                deferred.resolve(response["result"], textStatus, jqXHR);
                return;
            }
            if (response.error.data.type !== "session_invalid") {
                deferred.reject(response.error);
                return;
            }
            self.uid = false;
            self.on_session_invalid(function() {
                self.rpc(url, payload.params,
                    function() {
                        deferred.resolve.apply(deferred, arguments);
                    },
                    function(error, event) {
                        event.preventDefault();
                        deferred.reject.apply(deferred, arguments);
                    });
            });
        }).fail(function(jqXHR, textStatus, errorThrown) {
            self.on_rpc_response();
            var error = {
                code: -32098,
                message: "XmlHttpRequestError " + errorThrown,
                data: {type: "xhr"+textStatus, debug: jqXHR.responseText, objects: [jqXHR, errorThrown] }
            };
            deferred.reject(error);
        });
        return deferred.promise();
    },
    on_rpc_request: function() {
    },
    on_rpc_response: function() {
    },
    on_rpc_error: function(error) {
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
        this.db = this.get_cookie('db');
        this.login = this.get_cookie('login');
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
        this.set_cookie('db', this.db);
        this.set_cookie('login', this.login);
    },
    logout: function() {
        delete this.uid;
        delete this.session_id;
        delete this.db;
        delete this.login;
        this.set_cookie('uid', '');
        this.set_cookie('session_id', '');
        this.set_cookie('db', '');
        this.set_cookie('login', '');
        this.on_session_invalid(function() {});
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
                return JSON.parse(decodeURIComponent(cookie.substring(nameEQ.length)));
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
            this.element_id + '|' + name + '=' + encodeURIComponent(JSON.stringify(value)),
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
            self.module_list = result;
            var modules = self.module_list.join(',');
            if(self.debug || true) {
                self.rpc('/base/webclient/csslist', {"mods": modules}, self.do_load_css);
                self.rpc('/base/webclient/jslist', {"mods": modules}, self.do_load_js);
            } else {
                self.do_load_css(["/base/webclient/css?mods="+modules]);
                self.do_load_js(["/base/webclient/js?mods="+modules]);
            }
            openerp._modules_loaded = true;
        });
    },
    do_load_css: function (files) {
        _.each(files, function (file) {
            $('head').append($('<link>', {
                'href': file,
                'rel': 'stylesheet',
                'type': 'text/css'
            }));
        });
    },
    do_load_js: function(files) {
        var self = this;
        if(files.length != 0) {
            var file = files.shift();
            var tag = document.createElement('script');
            tag.type = 'text/javascript';
            tag.src = file;
            tag.onload = tag.onreadystatechange = function() {
                if ( (tag.readyState && tag.readyState != "loaded" && tag.readyState != "complete") || tag.onload_done )
                    return;
                tag.onload_done = true;
                self.do_load_js(files);
            };
            document.head.appendChild(tag);
        } else {
            this.on_modules_loaded();
        }
    },
    on_modules_loaded: function() {
        for(var j=0; j<this.module_list.length; j++) {
            var mod = this.module_list[j];
            if(this.module_loaded[mod])
                continue;
            openerp[mod] = {};
            // init module mod
            if(openerp._openerp[mod] != undefined) {
                openerp._openerp[mod](openerp);
                this.module_loaded[mod] = true;
            }
        }
    }
});

openerp.base.Notification =  openerp.base.Widget.extend({
    init: function(parent, element_id) {
        this._super(parent, element_id);
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
            text: text
        });
    }
});

openerp.base.Dialog = openerp.base.OldWidget.extend({
    dialog_title: "",
    identifier_prefix: 'dialog',
    init: function (parent, options) {
        var self = this;
        this._super(parent);
        this.options = {
            modal: true,
            width: 'auto',
            min_width: 0,
            max_width: '100%',
            height: 'auto',
            min_height: 0,
            max_height: '100%',
            autoOpen: false,
            buttons: {},
            beforeClose: function () {
                self.on_close();
            }
        };
        for (var f in this) {
            if (f.substr(0, 10) == 'on_button_') {
                this.options.buttons[f.substr(10)] = this[f];
            }
        }
        if (options) {
            this.set_options(options);
        }
    },
    set_options: function(options) {
        options = options || {};
        options.width = this.get_width(options.width || this.options.width);
        options.min_width = this.get_width(options.min_width || this.options.min_width);
        options.max_width = this.get_width(options.max_width || this.options.max_width);
        options.height = this.get_height(options.height || this.options.height);
        options.min_height = this.get_height(options.min_height || this.options.min_height);
        options.max_height = this.get_height(options.max_height || this.options.max_width);

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
        _.extend(this.options, options);
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
    start: function (auto_open) {
        this.$dialog = $('<div id="' + this.element_id + '"></div>').dialog(this.options);
        if (auto_open !== false) {
            this.open();
        }
        this._super();
    },
    open: function(options) {
        // TODO fme: bind window on resize
        if (this.template) {
            this.$element.html(this.render());
        }
        this.set_options(options);
        this.$dialog.dialog(this.options).dialog('open');
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
    }
});

openerp.base.CrashManager = openerp.base.Dialog.extend({
    identifier_prefix: 'dialog_crash',
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
            var split = error.data.fault_code.split('\n')[0].split(' -- ');
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

openerp.base.Loading =  openerp.base.Widget.extend({
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

openerp.base.Database = openerp.base.Widget.extend({
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
        
        var fetch_db = this.rpc("/base/database/get_list", {}, function(result) {
            self.db_list = result.db_list;
        });
        var fetch_langs = this.rpc("/base/session/get_lang_list", {}, function(result) {
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
        self.rpc('/base/database/progress', {
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
                self.stop();
                self.widget_parent.do_login(
                        info.db, admin.login, admin.password);
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
       	self.$option_id.html(QWeb.render("CreateDB", self));

        self.$option_id.find("form[name=create_db_form]").validate({
            submitHandler: function (form) {
                var fields = $(form).serializeArray();
                $.blockUI();
                self.rpc("/base/database/create", {'fields': fields}, function(result) {
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
                self.rpc("/base/database/drop", {'fields': fields}, function(result) {
                    if (result.error) {
                        self.display_error(result);
                        return;
                    }
                    $db_list.find(':selected').remove();
                    self.db_list.splice(_.indexOf(self.db_list, db, true), 1);
                    self.notification.notify("Dropping database", "The database '" + db + "' has been dropped");
                });
            }
        });
    },

    wait_for_file: function (token, cleanup) {
        var self = this,
            cookie_name = 'fileToken',
            cookie_length = cookie_name.length;
        this.backup_timer = setInterval(function () {
            var cookies = document.cookie.split(';');
            for(var i=0; i<cookies.length; ++i) {
                var cookie = cookies[i].replace(/^\s*/, '');
                if(!cookie.indexOf(cookie_name) === 0) { continue; }
                var cookie_val = cookie.substring(cookie_length + 1);
                if(parseInt(cookie_val, 10) !== token) { continue; }

                // clear waiter
                clearInterval(self.backup_timer);
                // clear cookie
                document.cookie = _.sprintf("%s=;expires=%s;path=/",
                    cookie_name, new Date().toGMTString());

                if (cleanup) { cleanup(); }
            }
        }, 100);
    },
    do_backup: function() {
        var self = this;
       	self.$option_id.html(QWeb.render("BackupDB", self));

        self.$option_id.find("form[name=backup_db_form]").validate({
            submitHandler: function (form) {
                $.blockUI();
                // need to detect when the file is done downloading (not used
                // yet, but we'll need it to fix the UI e.g. with a throbber
                // while dump is being generated), iframe load event only fires
                // when the iframe content loads, so we need to go smarter:
                // http://geekswithblogs.net/GruffCode/archive/2010/10/28/detecting-the-file-download-dialog-in-the-browser.aspx
                var $target = $('#backup-target'),
                      token = new Date().getTime();
                if (!$target.length) {
                    $target = $('<iframe id="backup-target" style="display: none;">')
                        .appendTo(document.body)
                        .load(function () {
                            $.unblockUI();
                            clearInterval(self.backup_timer);
                            var error = this.contentDocument.body
                                    .firstChild.data
                                    .split('|');
                            self.display_error({
                                title: error[0],
                                error: error[1]
                            });
                        });
                }
                $(form).find('input[name=token]').val(token);
                form.submit();

                self.wait_for_file(token, function () {
                    $.unblockUI();
                });
            }
        });
    },
    
    do_restore: function() {
        var self = this;
       	self.$option_id.html(QWeb.render("RestoreDB", self));
       	
       	self.$option_id.find("form[name=restore_db_form]").validate({
            submitHandler: function (form) {
                $.blockUI();
                $(form).ajaxSubmit({
                    url: '/base/database/restore',
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
                self.rpc("/base/database/change_password", {
                    'fields': $(form).serializeArray()
                }, function(result) {
                    if (result.error) {
                        self.display_error(result);
                        return;
                    }
                    self.notification.notify("Changed Password", "Password has been changed successfully");
                });
            }
        });
    }
});

openerp.base.Login =  openerp.base.Widget.extend({
    remember_creditentials: true,
    
    init: function(parent, element_id) {
        this._super(parent, element_id);
        this.has_local_storage = typeof(localStorage) != 'undefined';
        this.selected_db = null;
        this.selected_login = null;

        if (this.has_local_storage && this.remember_creditentials) {
            this.selected_db = localStorage.getItem('last_db_login_success');
            this.selected_login = localStorage.getItem('last_login_login_success');
        }
        if (jQuery.deparam(jQuery.param.querystring()).debug != undefined) {
            this.selected_db = this.selected_db || "trunk";
            this.selected_login = this.selected_login || "admin";
            this.selected_password = this.selected_password || "a";
        }
    },
    start: function() {
        var self = this;
        this.rpc("/base/database/get_list", {}, function(result) {
            self.db_list = result.db_list;
            self.display();
        }, function() {
            self.display();
        });
    },
    display: function() {
        var self = this;

        this.$element.html(QWeb.render("Login", this));
        this.database = new openerp.base.Database(
                this, "oe_database", "oe_db_options");

        this.$element.find('#oe-db-config').click(function() {
            self.database.start();
        });

        this.$element.find("form").submit(this.on_submit);
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
                    } else {
                        localStorage.setItem('last_db_login_success', '');
                        localStorage.setItem('last_login_login_success', '');
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
            callback: continuation
        });
    },
    on_logout: function() {
        this.session.logout();
    }
});

openerp.base.Header =  openerp.base.Widget.extend({
    init: function(parent, element_id) {
        this._super(parent, element_id);
    },
    start: function() {
        return this.do_update();
    },
    do_update: function () {
        this.$element.html(QWeb.render("Header", this));
        this.$element.find(".logout").click(this.on_logout);
        return this.shortcut_load();
    },
    shortcut_load :function(){
        var self = this;
        return this.rpc('/base/session/sc_list', {}, function(shortcuts) {
            self.session.sc_list = shortcuts;
            self.$element.find('.oe-shortcuts')
                .html(QWeb.render('Shortcuts', {'shortcuts': shortcuts}))
                .undelegate('li', 'click')
                .delegate('li', 'click', function(e) {
                    e.stopPropagation();
                    var id = $(this).data('id');
                    self.session.active_id = id;
                    self.rpc('/base/menu/action', {'menu_id':id}, function(ir_menu_data) {
                        if (ir_menu_data.action.length){
                            self.on_action(ir_menu_data.action[0][2]);
                        }
                    });
                });
        });
    },
    on_action: function(action) {
    },

    on_logout: function() {
        this.$element.find('#shortcuts ul li').remove();
    }
});

openerp.base.Menu =  openerp.base.Widget.extend({
    init: function(parent, element_id, secondary_menu_id) {
        this._super(parent, element_id);
        this.secondary_menu_id = secondary_menu_id;
        this.$secondary_menu = $("#" + secondary_menu_id).hide();
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
            this.session.active_id = id;
            this.rpc('/base/menu/action', {'menu_id': id},
                    this.on_menu_action_loaded);
        }

        $('.active', this.$element.add(this.$secondary_menu.show())).removeClass('active');
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

openerp.base.Homepage = openerp.base.Widget.extend({
});

openerp.base.Preferences = openerp.base.Widget.extend({
});

openerp.base.ImportExport = openerp.base.Widget.extend({
});

openerp.base.WebClient = openerp.base.Widget.extend({
    init: function(element_id) {
        this._super(null, element_id);

        QWeb.add_template("/base/static/src/xml/base.xml");
        var params = {};
        if(jQuery.param != undefined && jQuery.deparam(jQuery.param.querystring()).kitten != undefined) {
            this.$element.addClass("kitten-mode-activated");
        }
        this.$element.html(QWeb.render("Interface", params));

        this.session = new openerp.base.Session(this,"oe_errors");
        this.loading = new openerp.base.Loading(this,"oe_loading");
        this.crashmanager =  new openerp.base.CrashManager(this);
        this.crashmanager.start(false);

        // Do you autorize this ? will be replaced by notify() in controller
        openerp.base.Widget.prototype.notification = new openerp.base.Notification(this, "oe_notification");

        this.header = new openerp.base.Header(this, "oe_header");
        this.login = new openerp.base.Login(this, "oe_login");
        this.header.on_logout.add(this.login.on_logout);

        this.session.on_session_invalid.add(this.login.do_ask_login);
        this.session.on_session_valid.add_last(this.header.do_update);
        this.session.on_session_valid.add_last(this.on_logged);

        this.menu = new openerp.base.Menu(this, "oe_menu", "oe_secondary_menu");
        this.menu.on_action.add(this.on_menu_action);
        this.header.on_action.add(this.on_menu_action);
       
        
    },
    start: function() {
        this.session.start();
        this.header.start();
        this.login.start();
        this.menu.start();
        this.notification.notify("OpenERP Client", "The openerp client has been initialized.");
    },
    on_logged: function() {
        this.action_manager =  new openerp.base.ActionManager(this, "oe_app");
        this.action_manager.start();

        // if using saved actions, load the action and give it to action manager
        var parameters = jQuery.deparam(jQuery.param.querystring());
        if (parameters["s_action"] != undefined) {
            var key = parseInt(parameters["s_action"], 10);
            var self = this;
            this.rpc("/base/session/get_session_action", {key:key}, function(action) {
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
        var ds = new openerp.base.DataSetSearch(this, 'res.users');
        ds.read_ids([this.session.uid], ['action_id'], function (users) {
            var home_action = users[0].action_id;
            if (!home_action) {
                self.default_home();
                return;
            }
            self.execute_home_action(home_action[0], ds);
        })
    },
    default_home: function () { },
    /**
     * Bundles the execution of the home action
     *
     * @param {Number} action action id
     * @param {openerp.base.DataSet} dataset action executor
     */
    execute_home_action: function (action, dataset) {
        var self = this;
        this.rpc('/base/action/load', {
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
    on_menu_action: function(action) {
        this.action_manager.do_action(action);
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
