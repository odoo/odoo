/** @odoo-module **/

import { NavBar } from '@web/webclient/navbar/navbar';
import { useService, useBus } from '@web/core/utils/hooks';
import { registry } from "@web/core/registry";
import { patch } from 'web.utils';
import { EditMenuDialog } from '@website/components/dialog/edit_menu';
import { OptimizeSEODialog } from '@website/components/dialog/seo';
import {WebsiteAceEditor, AceEditorAdapterComponent} from '@website/components/ace_editor/ace_editor';

const websiteSystrayRegistry = registry.category('website_systray');
const {useState} = owl;

patch(NavBar.prototype, 'website_navbar', {
    setup() {
        this._super();
        this.websiteService = useService('website');
        this.dialogService = useService('dialog');
        this.websiteContext = useState(this.websiteService.context);
        this.aceEditor = WebsiteAceEditor;

        if (this.env.debug) {
            registry.category('website_systray').add('DebugMenu', registry.category('systray').get('web.debug_mode_menu'), { sequence: 100 });
        }

        useBus(websiteSystrayRegistry, 'EDIT-WEBSITE', () => this.render(true));
        useBus(websiteSystrayRegistry, 'CONTENT-UPDATED', () => this.render(true));

        this.toggleAceEditor = (show) => {
            this.websiteContext.showAceEditor = show;
        };

        this.websiteEditingMenus = {
            'website.menu_edit_menu': {
                component: EditMenuDialog,
                isDisplayed: () => !!this.websiteService.currentWebsite,
            },
            'website.menu_optimize_seo': {
                component: OptimizeSEODialog,
                isDisplayed: () => this.websiteService.currentWebsite && !!this.websiteService.currentWebsite.metadata.mainObject,
            },
            'website.menu_ace_editor': {
                openWidget: () => this.toggleAceEditor(true),
                isDisplayed: () => this.canShowAceEditor(),
            },
        };
    },

    filterWebsiteMenus(sections) {
        const filteredSections = [];
        for (const section of sections) {
            if (!this.websiteEditingMenus[section.xmlid] || this.websiteEditingMenus[section.xmlid].isDisplayed()) {
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
    getSystrayItems() {
        if (this.websiteService.currentWebsite) {
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
    getCurrentAppSections() {
        const currentAppSections = this._super();
        if (this.currentApp && this.currentApp.xmlid === 'website.menu_website_configuration') {
            return this.filterWebsiteMenus(currentAppSections);
        }
        return currentAppSections;
    },

    /**
     * @overrid
     */
    onNavBarDropdownItemSelection(menu) {
        const websiteMenu = this.websiteEditingMenus[menu.xmlid];
        if (websiteMenu) {
            return websiteMenu.openWidget ? websiteMenu.openWidget() : this.dialogService.add(websiteMenu.component, websiteMenu.props, websiteMenu.options);
        }
        return this._super(menu);
    },

    canShowAceEditor() {
        return this.websiteService.pageDocument && this.websiteService.pageDocument.documentElement.dataset.viewXmlid
        && !this.websiteContext.showNewContentModal && !this.websiteContext.edition;
    },
});

NavBar.components.AceEditorAdapterComponent = AceEditorAdapterComponent;
