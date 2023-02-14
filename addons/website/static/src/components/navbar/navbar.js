/** @odoo-module **/

import { NavBar } from '@web/webclient/navbar/navbar';
import { useService } from '@web/core/utils/hooks';
import { registry } from "@web/core/registry";
import { patch } from 'web.utils';
import { useState, useEffect } from '@odoo/owl';

const websiteSystrayRegistry = registry.category('website_systray');

patch(NavBar.prototype, 'website_navbar', {
    setup() {
        this._super();
        this.websiteService = useService('website');
        this.websiteCustomMenus = useService('website_custom_menus');
        this.currentWebsite = useState(this.websiteService.currentWebsite);
        this.websiteContext = useState(this.websiteService.context);

        useEffect(() => {
            // Need a re-render when the metadata is changed as systray items
            // use it to know if they should be displayed or not.
            if (this.websiteContext.displaySystray) {
                this.adapt();
            }
        }, () => [this.currentWebsite.metadata]);

        if (this.env.debug && !websiteSystrayRegistry.contains('web.debug_mode_menu')) {
            websiteSystrayRegistry.add('web.debug_mode_menu', registry.category('systray').get('web.debug_mode_menu'), {sequence: 100});
        }

    },

    /**
     * @override
     */
    get systrayItems() {
        if (this.websiteContext.displaySystray && this.websiteService.isRestrictedEditor) {
            return websiteSystrayRegistry
                .getEntries()
                .map(([key, value], index) => ({ key, ...value, index }))
                .filter((item) => ('isDisplayed' in item ? item.isDisplayed(this.env) : true))
                .reverse();
        }
        return this._super();
    },

    /**
     * @override
     */
    get currentAppSections() {
        const currentAppSections = this._super();
        if (this.currentApp && this.currentApp.xmlid === 'website.menu_website_configuration') {
            return this.websiteCustomMenus.addCustomMenus(currentAppSections).filter(section => section.childrenTree.length);
        }
        return currentAppSections;
    },

    /**
     * @override
     */
    onNavBarDropdownItemSelection(menu) {
        const websiteMenu = this.websiteCustomMenus.get(menu.xmlid);
        if (websiteMenu) {
            return this.websiteCustomMenus.open(menu);
        }
        return this._super(menu);
    },
});
