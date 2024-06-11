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
     * @override
     */
    get currentAppSections() {
        const currentAppSections = super.currentAppSections;
        if (this.currentApp && this.currentApp.xmlid === 'website.menu_website_configuration') {
            return this.websiteCustomMenus.addCustomMenus(currentAppSections).filter(section => section.childrenTree.length);
        }
        return currentAppSections;
    },

    /**
     * This dummy setter is only here to prevent conflicts between the
     * Enterprise BurgerMenue extension and the Website BurgerMenu patch.
     */
    set currentAppSections(_) {},

    /**
     * @override
     */
    async _onMenuClicked(menu) {
        const websiteMenu = this.websiteCustomMenus.get(menu.xmlid);
        if (websiteMenu) {
            this.websiteCustomMenus.open(menu);
            this._closeBurger();
        } else {
            super._onMenuClicked(menu);
        }
    },
});
