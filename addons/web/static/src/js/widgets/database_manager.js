odoo.define('web.DatabaseManager', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var framework = require('web.framework');
var Widget = require('web.Widget');

var _t = core._t;
var QWeb = core.qweb;

var DataBaseManager = Widget.extend({
    init: function(parent) {
        this._super(parent);
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
        core.bus.trigger('web_client_toggle_bars', true);
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
        framework.blockUI();
        $.unblockUI = function () {};
    },
    /**
     * Reinstates $.unblockUI so third parties can play with blockUI, and
     * unblocks the UI
     */
    unblockUI: function () {
        $.unblockUI = framework.unblockUI;
        framework.unblockUI();
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
        return new Dialog(this, {
            size: 'medium',
            title: error.title,
            $content: $('<div>').html(error.error)
        }).open();
    },
    do_create: function(form) {
        var fields = $(form).serializeArray();
        this.rpc("/web/database/create", {'fields': fields}).done(function(result) {
            if (result) {
                framework.redirect('/web');
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
        framework.redirect('/web');
    }
});

core.action_registry.add("database_manager", DataBaseManager);

return DataBaseManager;

});
