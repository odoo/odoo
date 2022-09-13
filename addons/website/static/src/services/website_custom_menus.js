/** @odoo-module **/

import { registry } from "@web/core/registry";
import { EditMenuDialog } from '@website/components/dialog/edit_menu';
import { OptimizeSEODialog } from '@website/components/dialog/seo';
import {PagePropertiesDialog} from '@website/components/dialog/page_properties';

/**
 * This service displays contextual menus, depending of the state of the
 * website. These menus are defined in xml with the "website_preview" action,
 * which is overriden here for displaying dialogs, or regular components that
 * are not client actions.
 */
export const websiteCustomMenus = {
    dependencies: ['website', 'orm', 'dialog', 'ui'],
    start(env, { website, orm, dialog, ui }) {
        const services = { website, orm, dialog, ui };
        return {
            get(xmlId) {
                return registry.category('website_custom_menus').get(xmlId, null);
            },
            open(xmlId) {
                const menu = this.get(xmlId);
                if (menu.openWidget) {
                    return menu.openWidget(services);
                }
                return dialog.add(
                    menu.Component,
                    menu.getProps && menu.getProps(services),
                );
            },
            addCustomMenus(sections) {
                const filteredSections = [];
                for (const section of sections) {
                    const isWebsiteCustomMenu = !!this.get(section.xmlid);
                    const displayWebsiteCustomMenu = isWebsiteCustomMenu && website.isRestrictedEditor && this.get(section.xmlid).isDisplayed(env);
                    if (!isWebsiteCustomMenu || displayWebsiteCustomMenu) {
                        let subSections = [];
                        if (section.childrenTree.length) {
                            subSections = this.addCustomMenus(section.childrenTree);
                        }
                        filteredSections.push(Object.assign({}, section, {childrenTree: subSections}));
                    }
                }
                return filteredSections;
            },
        };
    }
};
registry.category('services').add('website_custom_menus', websiteCustomMenus);

registry.category('website_custom_menus').add('website.menu_edit_menu', {
    Component: EditMenuDialog,
    isDisplayed: (env) => !!env.services.website.currentWebsite
        && env.services.website.isDesigner
        && !env.services.ui.isSmall,
});
registry.category('website_custom_menus').add('website.menu_optimize_seo', {
    Component: OptimizeSEODialog,
    isDisplayed: (env) => env.services.website.currentWebsite
        && !!env.services.website.currentWebsite.metadata.mainObject,
});
registry.category('website_custom_menus').add('website.menu_current_page', {
    isDisplayed: (env) => !!env.services.website.currentWebsite
        && !!env.services.website.pageDocument,
},);
registry.category('website_custom_menus').add('website.menu_ace_editor', {
    openWidget: (services) => services.website.context.showAceEditor = true,
    isDisplayed: (env) => env.services.website.currentWebsite
        && env.services.website.currentWebsite.metadata.viewXmlid
        && !env.services.ui.isSmall,
});
registry.category('website_custom_menus').add('website.menu_page_properties', {
    Component: PagePropertiesDialog,
    isDisplayed: (env) => env.services.website.currentWebsite
        && !!env.services.website.currentWebsite.metadata.mainObject
        && env.services.website.currentWebsite.metadata.mainObject.model === 'website.page',
    getProps: (services) => ({
        onRecordSaved: (record) => {
            return services.orm.read('website.page', [record.resId], ['url']).then(res => {
                services.website.goToWebsite({websiteId: record.data.website_id[0], path: res[0]['url']});
            });
        },
    })
});
