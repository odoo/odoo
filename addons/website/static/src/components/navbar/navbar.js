/** @odoo-module **/

import { NavBar } from '@web/webclient/navbar/navbar';
import { useService, useBus } from '@web/core/utils/hooks';
import { registry } from "@web/core/registry";
import { patch } from 'web.utils';
import { EditMenuDialog } from '@website/components/dialog/edit_menu';
import { OptimizeSEODialog } from '@website/components/dialog/seo';
import {PagePropertiesDialog} from '@website/components/dialog/page_properties';

const websiteSystrayRegistry = registry.category('website_systray');
const { useState } = owl;

patch(NavBar.prototype, 'website_navbar', {
    setup() {
        this._super();
        this.orm = useService('orm');
        this.websiteService = useService('website');
        this.websiteContext = useState(this.websiteService.context);

        // The navbar is rerendered with an event, as it can not naturally be
        // with props/state (the WebsitePreview client action and the navbar
        // are not related).
        useBus(websiteSystrayRegistry, 'EDIT-WEBSITE', () => this.render(true));

        if (this.env.debug && !websiteSystrayRegistry.contains('web.debug_mode_menu')) {
            websiteSystrayRegistry.add('web.debug_mode_menu', registry.category('systray').get('web.debug_mode_menu'), {sequence: 100});
        }

        useBus(websiteSystrayRegistry, 'CONTENT-UPDATED', () => this.render(true));

        this.websiteEditingMenus = {
            'website.menu_edit_menu': {
                Component: EditMenuDialog,
                isDisplayed: () => !!this.websiteService.currentWebsite && this.websiteService.isDesigner,
            },
            'website.menu_optimize_seo': {
                Component: OptimizeSEODialog,
                isDisplayed: () => this.websiteService.currentWebsite && !!this.websiteService.currentWebsite.metadata.mainObject,
            },
            'website.menu_ace_editor': {
                openWidget: () => this.websiteContext.showAceEditor = true,
                isDisplayed: () => this.canShowAceEditor(),
            },
            'website.menu_page_properties': {
                Component: PagePropertiesDialog,
                isDisplayed: () => this.canShowPageProperties(),
                getProps: () => ({
                    onRecordSaved: (record) => {
                        return this.orm.read('website.page', [record.resId], ['url']).then(res => {
                            this.websiteService.goToWebsite({websiteId: record.data.website_id[0], path: res[0]['url']});
                        });
                    },
                })
            },
        };
    },

    filterWebsiteMenus(sections) {
        const filteredSections = [];
        for (const section of sections) {
            const isWebsiteCustomMenu = this.websiteEditingMenus[section.xmlid];
            const displayWebsiteCustomMenu = isWebsiteCustomMenu && this.websiteService.isPublisher && this.websiteEditingMenus[section.xmlid].isDisplayed();
            if (!isWebsiteCustomMenu || displayWebsiteCustomMenu) {
                let subSections = [];
                if (section.childrenTree.length) {
                    subSections = this.filterWebsiteMenus(section.childrenTree);
                }
                filteredSections.push(Object.assign({}, section, {childrenTree: subSections}));
            }
        }
        return filteredSections;
    },

    /**
     * @override
     */
    get systrayItems() {
        if (this.websiteService.currentWebsite && this.websiteService.isPublisher) {
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
            return this.filterWebsiteMenus(currentAppSections).filter(section => section.childrenTree.length);
        }
        return currentAppSections;
    },

    /**
     * @override
     */
    onNavBarDropdownItemSelection(menu) {
        const websiteMenu = this.websiteEditingMenus[menu.xmlid];
        if (websiteMenu) {
            return websiteMenu.openWidget ?
                websiteMenu.openWidget() :
                this.websiteService.openMenuDialog(
                    websiteMenu.Component,
                    websiteMenu.getProps && websiteMenu.getProps(),
                );
        }
        return this._super(menu);
    },

    canShowPageProperties() {
        return this.websiteService.currentWebsite
            && !!this.websiteService.currentWebsite.metadata.mainObject
            && this.websiteService.currentWebsite.metadata.mainObject.model === 'website.page';
    },

    canShowAceEditor() {
        return this.websiteService.currentWebsite && this.websiteService.currentWebsite.metadata.viewXmlid
            && !this.websiteContext.showNewContentModal && !this.websiteContext.edition;
    },
});
