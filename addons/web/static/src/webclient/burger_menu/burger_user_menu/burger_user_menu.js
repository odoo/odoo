// @ts-check

/** @module @web/webclient/burger_menu/burger_user_menu/burger_user_menu - Mobile variant of the user menu shown inside the burger menu overlay */

import { UserMenu } from "@web/webclient/user_menu/user_menu";

/** Mobile variant of the user menu shown inside the burger menu overlay. */
export class BurgerUserMenu extends UserMenu {
    static template = "web.BurgerUserMenu";
    static props = {
        ...UserMenu.props,
        onMenuClicked: { type: Function, optional: true },
    };
    /**
     * Wrap item click callback to also notify the burger menu overlay.
     * @param {Function} callback - Original menu item click handler
     * @returns {(ev: Event) => void} Wrapped handler that calls both callback and onMenuClicked
     */
    _onItemClicked(callback) {
        return (ev) => {
            callback(ev);
            this.props.onMenuClicked?.(ev);
        };
    }
}
