import { t, useProps } from "@odoo/owl";
import { UserMenu, userMenuProps } from "@web/webclient/user_menu/user_menu";

export class BurgerUserMenu extends UserMenu {
    static template = "web.BurgerUserMenu";
    props = useProps({
        ...userMenuProps,
        onMenuClicked: t.function().optional(),
    });
    _onItemClicked(callback) {
        return async (ev) => {
            // The callback may rely on this component (e.g. an orm call):
            // closing the burger menu destroys it, so wait for the callback.
            try {
                await callback(ev);
            } finally {
                this.props.onMenuClicked?.(ev);
            }
        };
    }
}
