import { UserMenu } from "@web/webclient/user_menu/user_menu";

export class BurgerUserMenu extends UserMenu {
    static template = "web.BurgerUserMenu";
    static props = {
        ...UserMenu.props,
        onMenuClicked: { type: Function, optional: true },
    };
    _onItemClicked(callback) {
        return (ev) => {
            callback(ev);
            this.props.onMenuClicked?.(ev);
        };
    }
}
