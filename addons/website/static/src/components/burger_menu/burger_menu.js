/** @odoo-module **/

import { BurgerMenu } from '@web/webclient/burger_menu/burger_menu';
import { useService } from '@web/core/utils/hooks';
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const websiteSystrayRegistry = registry.category('website_systray');

patch(BurgerMenu.prototype, {
    setup() {
        super.setup();
        this.websiteCustomMenus = useService('website_custom_menus');

        if (!websiteSystrayRegistry.contains('burger_menu')) {
            websiteSystrayRegistry.add('burger_menu', registry.category('systray').get('burger_menu'), {sequence: 0});
        }
    },

    /**
     * @deprecated The app sections are no longer displayed in the burger
     * menu, but in the `NavBar` app menu sidebar.
     */
    get currentAppSections() {
        return [];
    },

    /**
     * @deprecated Kept for backward compatibility with existing extensions.
     */
    set currentAppSections(_) {},

    /**
     * @deprecated The app sections are no longer displayed in the burger
     * menu, see `_onMenuClicked` in the `NavBar` patch.
     */
    async _onMenuClicked(menu) {
        const websiteMenu = this.websiteCustomMenus.get(menu.xmlid);
        if (websiteMenu) {
            await this.websiteCustomMenus.open(menu);
            this._closeBurger();
        }
    },
});
