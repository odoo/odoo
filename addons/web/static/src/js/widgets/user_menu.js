odoo.define('web.UserMenu', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var framework = require('web.framework');
var Model = require('web.Model');
var session = require('web.session');
var Widget = require('web.Widget');

var _t = core._t;
var QWeb = core.qweb;

var SystrayMenu = Widget.extend({
    template: "UserMenu",
    init: function(parent) {
        this._super(parent);
        this.update_promise = $.Deferred().resolve();
    },
    start: function() {
        var self = this;
        this.$el.on('click', '.dropdown-menu li a[data-menu]', function(ev) {
            ev.preventDefault();
            var f = self['on_menu_' + $(this).data('menu')];
            if (f) {
                f($(this));
            }
        });
        this.$el.parent().show();
        return this._super.apply(this, arguments);
    },
    do_update: function () {
        var self = this;
        var fct = function() {
            var $avatar = self.$el.find('.oe_topbar_avatar');
            $avatar.attr('src', $avatar.data('default-src'));
            if (!session.uid)
                return;
            var func = new Model("res.users").get_func("read");
            return self.alive(func(session.uid, ["name", "company_id"])).then(function(res) {
                var topbar_name = res.name;
                if(session.debug)
                    topbar_name = _.str.sprintf("%s (%s)", topbar_name, session.db);
                if(res.company_id[0] > 1)
                    topbar_name = _.str.sprintf("%s (%s)", topbar_name, res.company_id[1]);
                self.$el.find('.oe_topbar_name').text(topbar_name);
                if (!session.debug) {
                    topbar_name = _.str.sprintf("%s (%s)", topbar_name, session.db);
                }
                var avatar_src = session.url('/web/binary/image', {model:'res.users', field: 'image_small', id: session.uid});
                $avatar.attr('src', avatar_src);

                core.bus.trigger('resize');  // Re-trigger the reflow logic
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
        this.getParent().clear_uncommitted_changes().then(function() {
            self.rpc("/web/action/load", { action_id: "base.action_res_users_my" }).done(function(result) {
                result.res_id = session.uid;
                self.getParent().action_manager.do_action(result);
            });
        });
    },
    on_menu_account: function() {
        this.getParent().clear_uncommitted_changes().then(function() {
            var P = new Model('ir.config_parameter');
            P.call('get_param', ['database.uuid']).then(function(dbuuid) {
                var state = {
                            'd': session.db,
                            'u': window.location.protocol + '//' + window.location.host,
                        };
                var params = {
                    response_type: 'token',
                    client_id: dbuuid || '',
                    state: JSON.stringify(state),
                    scope: 'userinfo',
                };
                framework.redirect('https://accounts.odoo.com/oauth2/auth?'+$.param(params));
            }).fail(function(result, ev){
                ev.preventDefault();
                framework.redirect('https://accounts.odoo.com/account');
            });
        });
    },
    on_menu_about: function() {
        var self = this;
        self.rpc("/web/webclient/version_info", {}).done(function(res) {
            var $help = $(QWeb.render("UserMenu.about", {version_info: res}));
            $help.find('a.oe_activate_debug_mode').click(function (e) {
                e.preventDefault();
                window.location = $.param.querystring( window.location.href, 'debug');
            });
            new Dialog(this, {
                size: 'medium',
                dialogClass: 'o_act_window',
                title: _t("About"),
                $content: $help
            }).open();
        });
    },
});

return SystrayMenu;
});
