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

var UserMenu = Widget.extend({
    template: "UserMenu",
    start: function() {
        var self = this;
        this.$el.on('click', '.dropdown-menu li a[data-menu]', function(ev) {
            ev.preventDefault();
            var f = self['on_menu_' + $(this).data('menu')];
            if (f) {
                f($(this));
            }
        });
        return this._super.apply(this, arguments).then(function () {
            return self.do_update();
        });
    },
    do_update: function () {
        var $avatar = this.$('.oe_topbar_avatar');
        if (!session.uid) {
            $avatar.attr('src', $avatar.data('default-src'));
            return $.when();
        }
        var topbar_name = session.name;
        if(session.debug) {
            topbar_name = _.str.sprintf("%s (%s)", topbar_name, session.db);
        }
        this.$('.oe_topbar_name').text(topbar_name);
        var avatar_src = session.url('/web/image', {model:'res.users', field: 'image_small', id: session.uid});
        $avatar.attr('src', avatar_src);
    },
    on_menu_documentation: function () {
        window.open('https://www.odoo.com/documentation/user', '_blank');
    },
    on_menu_support: function () {
        window.open('https://www.odoo.com/buy', '_blank');
    },
    on_menu_settings: function() {
        var self = this;
        this.trigger_up('clear_uncommitted_changes', {
            callback: function() {
                self.rpc("/web/action/load", { action_id: "base.action_res_users_my" }).done(function(result) {
                    result.res_id = session.uid;
                    self.do_action(result);
                });
            },
        });
    },
    on_menu_account: function() {
        this.trigger_up('clear_uncommitted_changes', {
            callback: function() {
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
            },
        });
    },
    on_menu_logout: function() {
        this.trigger_up('clear_uncommitted_changes', {
            callback: this.do_action.bind(this, 'logout'),
        });
    },
});

return UserMenu;
});
