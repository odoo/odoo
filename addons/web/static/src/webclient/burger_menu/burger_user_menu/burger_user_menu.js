import { t, useProps } from "@odoo/owl";
import { UserMenu, userMenuProps } from "@web/webclient/user_menu/user_menu";

export class BurgerUserMenu extends UserMenu {
    static template = "web.BurgerUserMenu";
    props = useProps({
        ...userMenuProps,
        onMenuClicked: t.function().optional(),
    });
    _onItemClicked(callback) {
        return (ev) => {
            callback(ev);
            this.props.onMenuClicked?.(ev);
        };
    }
}
