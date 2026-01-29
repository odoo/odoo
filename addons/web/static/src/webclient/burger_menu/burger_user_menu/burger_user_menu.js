/** @odoo-module **/

import { UserMenu } from "@web/webclient/user_menu/user_menu";

export class BurgerUserMenu extends UserMenu {
    _onItemClicked(callback) {
        return (ev) => {
            callback(ev);
            this.props.onMenuClicked?.(ev);
        };
    }
}
BurgerUserMenu.template = "web.BurgerUserMenu";
BurgerUserMenu.props = {
    ...UserMenu.props,
    onMenuClicked: { type: Function, optional: true },
};
