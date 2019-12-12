odoo.define('web.UserMenu', function (require) {
"use strict";

const OwlDialog = require('web.OwlDialog');
const { useListener } = require('web.custom_hooks');

class ShortCuts extends owl.Component {};
ShortCuts.template = 'UserMenu.shortcuts';

/**
 * This widget is appended by the webclient to the right of the navbar.
 * It displays the avatar and the name of the logged user (and optionally the
 * db name, in debug mode).
 * If clicked, it opens a dropdown allowing the user to perform actions like
 * editing its preferences, accessing the documentation, logging out...
 */
class UserMenu extends owl.Component {
    constructor() {
        super(...arguments);
        useListener('click', '[data-menu]', this._onMenuClicked);
        this.state = owl.hooks.useState({
            dialog: null,
        });
    }
    get avatarSRC() {
        return this.env.session.url('/web/image', {
            model: 'res.users',
            field: 'image_128',
            id: this.env.session.uid,
        });
    }
    _onMenuClicked(ev) {
        ev.preventDefault();
        const menu = ev.target.dataset.menu;
        this['_onMenu' + menu.charAt(0).toUpperCase() + menu.slice(1)]();
    }
    /**
     * @private
     */
    _onMenuDocumentation() {
        window.open('https://www.odoo.com/documentation/user', '_blank');
    }
    /**
     * @private
     */
    _onMenuLogout() {
        const action = 'logout';
        this.env.bus.trigger('do-action', {action});
    }
    /**
     * @private
     */
    async _onMenuSettings() {
        const action = await this.rpc({
            model: "res.users",
            method: "action_get"
        });
        action.res_id = this.env.session.uid;
        this.env.bus.trigger('do-action', {action});
    }
    /**
     * @private
     */
    _onMenuSupport() {
        window.open('https://www.odoo.com/buy', '_blank');
    }
    /**
     * @private
     */
    _onMenuShortcuts() {
        this.state.dialog = {
            Component: ShortCuts,
            dialogProps: {
                contentClass:'o_act_window',
                title: this.env._t("Keyboard Shortcuts"),
            }
        };
    }
}
UserMenu.template = 'web.OwlUserMenu';
UserMenu.components = { OwlDialog };

return UserMenu;
});
