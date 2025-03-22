/** @odoo-module **/

import { NavBar } from '@web/webclient/navbar/navbar';
import { useService, useBus } from '@web/core/utils/hooks';
import { registry } from "@web/core/registry";
import { patch } from 'web.utils';

const websiteSystrayRegistry = registry.category('website_systray');
const { useEffect } = owl;

patch(NavBar.prototype, 'website_navbar', {
    setup() {
        this._super();
        this.websiteService = useService('website');
        this.websiteCustomMenus = useService('website_custom_menus');

        // The navbar is rerendered with an event, as it can not naturally be
        // with props/state (the WebsitePreview client action and the navbar
        // are not related).
        useBus(websiteSystrayRegistry, 'EDIT-WEBSITE', () => this.render(true));

        if (this.env.debug && !websiteSystrayRegistry.contains('web.debug_mode_menu')) {
            websiteSystrayRegistry.add('web.debug_mode_menu', registry.category('systray').get('web.debug_mode_menu'), {sequence: 100});
        }
        // Similar to what is done in web/navbar. When the app menu or systray
        // is updated, we need to adapt the navbar so that the "more" menu
        // can be computed.
        let adaptCounter = 0;
        const renderAndAdapt = () => {
            this.render(true);
            adaptCounter++;
        };
        useEffect(
            (adaptCounter) => {
                // We do not want to adapt on the first render
                // as the super class already does it.
                if (adaptCounter > 0) {
                    this.adapt();
                }
            },
            () => [adaptCounter]
        );

        useBus(websiteSystrayRegistry, 'CONTENT-UPDATED', renderAndAdapt);
    },

    /**
     * @override
     */
    get systrayItems() {
        if (this.websiteService.currentWebsite) {
            const websiteItems = websiteSystrayRegistry
                .getEntries()
                .map(([key, value], index) => ({ key, ...value, index }))
                .filter((item) => ('isDisplayed' in item ? item.isDisplayed(this.env) : true))
                .reverse();
            // Do not override the regular Odoo navbar if the only visible
            // elements are the debug items.
            if (!websiteItems.every((item) => ['burger_menu', 'web.debug_mode_menu'].includes(item.key))) {
                return websiteItems;
            }
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
