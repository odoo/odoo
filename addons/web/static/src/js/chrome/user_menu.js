odoo.define('web.UserMenu', function (require) {
"use strict";

/**
 * This widget is appended by the webclient to the right of the navbar.
 * It displays the avatar and the name of the logged user (and optionally the
 * db name, in debug mode).
 * If clicked, it opens a dropdown allowing the user to perform actions like
 * editing its preferences, accessing the documentation, logging out...
 */

var core = require('web.core');
var framework = require('web.framework');
var Dialog = require('web.Dialog');
var Widget = require('web.Widget');

var _t = core._t;
var QWeb = core.qweb;

var UserMenu = Widget.extend({
    template: 'UserMenu',

    /**
     * @override
     * @returns {Deferred}
     */
    start: function () {
        var self = this;
        var session = this.getSession();
        this.$el.on('click', '[data-menu]', function (ev) {
            ev.preventDefault();
            var menu = $(this).data('menu');
            self['_onMenu' + menu.charAt(0).toUpperCase() + menu.slice(1)]();
        });
        return this._super.apply(this, arguments).then(function () {
            var $avatar = self.$('.oe_topbar_avatar');
            if (!session.uid) {
                $avatar.attr('src', $avatar.data('default-src'));
                return $.when();
            }
            var topbar_name = session.name;
            if (session.debug) {
                topbar_name = _.str.sprintf("%s (%s)", topbar_name, session.db);
            }
            self.$('.oe_topbar_name').text(topbar_name);
            var avatar_src = session.url('/web/image', {
                model:'res.users',
                field: 'image_small',
                id: session.uid,
            });
            $avatar.attr('src', avatar_src);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onMenuAccount: function () {
        var self = this;
        this.trigger_up('clear_uncommitted_changes', {
            callback: function () {
                self._rpc({route: '/web/session/account'})
                    .then(function (url) {
                        framework.redirect(url);
                    })
                    .fail(function (result, ev){
                        ev.preventDefault();
                        framework.redirect('https://accounts.odoo.com/account');
                    });
            },
        });
    },
    /**
     * @private
     */
    _onMenuDocumentation: function () {
        window.open('https://www.odoo.com/documentation/user', '_blank');
    },
    /**
     * @private
     */
    _onMenuLogout: function () {
        this.trigger_up('clear_uncommitted_changes', {
            callback: this.do_action.bind(this, 'logout'),
        });
    },
    /**
     * @private
     */
    _onMenuSettings: function () {
        var self = this;
        var session = this.getSession();
        this.trigger_up('clear_uncommitted_changes', {
            callback: function () {
                self._rpc({
                        route: "/web/action/load",
                        params: {
                            action_id: "base.action_res_users_my",
                        },
                    })
                    .done(function (result) {
                        result.res_id = session.uid;
                        self.do_action(result);
                    });
            },
        });
    },
    /**
     * @private
     */
    _onMenuSupport: function () {
        window.open('https://www.odoo.com/buy', '_blank');
    },
    /**
     * @private
     */
    _onMenuShortcuts: function() {
        new Dialog(this, {
            size: 'large',
            dialogClass: 'o_act_window',
            title: _t("Keyboard Shortcuts"),
            $content: $(QWeb.render("UserMenu.shortcuts"))
        }).open();
    },
});

return UserMenu;

});
