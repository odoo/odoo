/** @odoo-module **/

import { NavBar } from '@web/webclient/navbar/navbar';
import { useService } from '@web/core/utils/hooks';
import { registry } from "@web/core/registry";
import { patch } from 'web.utils';

const websiteSystrayRegistry = registry.category('website_systray');

const { useState, useEffect } = owl;

patch(NavBar.prototype, 'website_navbar', {
    setup() {
        this._super();
        this.websiteService = useService('website');
        this.websiteCustomMenus = useService('website_custom_menus');

        if (this.env.debug && !websiteSystrayRegistry.contains('web.debug_mode_menu')) {
            websiteSystrayRegistry.add('web.debug_mode_menu', registry.category('systray').get('web.debug_mode_menu'), {sequence: 100});
        }

        this.currentWebsite = useState(this.websiteService.currentWebsite);

        useEffect(isLoaded => {
            // When the website is loaded, all the website systray elements
            // have been rendered and the navbar must be adapted accordingly.
            if (isLoaded) {
                this.adapt();
            }
        }, () => [this.isWebsiteLoaded()]);
    },

    /**
     * @override
     */
    get systrayItems() {
        if (this.websiteService.isRestrictedEditor && this.isWebsiteLoaded()) {
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

    /**
     * A website is considered as loaded when it has metadata. When that value
     * is updated, the navbar will rerender and adapt.
     *
     * @returns {boolean}
     */
    isWebsiteLoaded() {
        return !!Object.keys(this.currentWebsite.metadata).length;
    },
});
