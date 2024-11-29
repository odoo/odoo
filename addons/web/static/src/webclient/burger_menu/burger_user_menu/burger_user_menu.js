import { UserMenu } from "@web/webclient/user_menu/user_menu";

export class BurgerUserMenu extends UserMenu {
    static template = "web.BurgerUserMenu";
    _onItemClicked(callback) {
        callback();
    }
}
