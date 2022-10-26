/** @odoo-module **/

import { UserMenu } from "@web/webclient/user_menu/user_menu";

export class BurgerUserMenu extends UserMenu {
    _onItemClicked(callback) {
        callback();
    }
}
BurgerUserMenu.template = "web.BurgerUserMenu";
