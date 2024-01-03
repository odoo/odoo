/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
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
            open(customMenu) {
                const menuConfig = this.get(customMenu.xmlid);
                if (menuConfig.openWidget) {
                    return menuConfig.openWidget(services);
                }
                const menuProps = {
                    ...(menuConfig.getProps && menuConfig.getProps(services)),
                    // Values on 'dynamicProps' are retrieved after the content is loaded (e.g. id of
                    // the content menu to be edited).
                    ...customMenu.dynamicProps,
                };
                return dialog.add(
                    menuConfig.Component,
                    menuProps,
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
                        if (section.xmlid === 'website.custom_menu_edit_menu') {
                            // Hack: this code will simulate an XML pre-configured navbar menuitem to edit each
                            // content menu found on the current page by duplicating one menuitem with
                            // different data (name, dialog props...). this will prevent breaking the current
                            // 'navbar menus' display system.
                            filteredSections.push(...website.currentWebsite.metadata.contentMenus.map((menu, index) => ({
                                ...section,
                                name: _t("Edit %s", menu[0]),
                                dynamicProps: {rootID: parseInt(menu[1], 10)},
                                // Prevent a 't-foreach' duplicate key on menus template.
                                id: `${section.id}-${index}`,
                            })));
                        } else {
                            filteredSections.push(Object.assign({}, section, {childrenTree: subSections}));
                        }
                    }
                }
                for (const section of filteredSections) {
                    section.childrenTree = section.childrenTree.filter(
                        // Exclude non-leaf node having no visible sub-element.
                        tree => !(tree.children.length && !tree.childrenTree.length)
                    );
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
        && !env.services.ui.isSmall
        && !env.services.website.currentWebsite.metadata.translatable,
});
registry.category('website_custom_menus').add('website.menu_optimize_seo', {
    Component: OptimizeSEODialog,
    isDisplayed: (env) => env.services.website.currentWebsite
        && env.services.website.isRestrictedEditor
        && !!env.services.website.currentWebsite.metadata.canOptimizeSeo,
});
registry.category('website_custom_menus').add('website.menu_ace_editor', {
    openWidget: (services) => services.website.context.showResourceEditor = true,
    isDisplayed: (env) => env.services.website.currentWebsite
        && env.services.website.currentWebsite.metadata.viewXmlid
        && !env.services.ui.isSmall,
});
registry.category('website_custom_menus').add('website.menu_page_properties', {
    Component: PagePropertiesDialog,
    isDisplayed: (env) => env.services.website.currentWebsite
        && env.services.website.isDesigner
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
registry.category('website_custom_menus').add('website.custom_menu_edit_menu', {
    Component: EditMenuDialog,
    // 'isDisplayed' === true => at least 1 content menu was found on the page. This
    // menuitem will be cloned (in 'addCustomMenus()') to edit every content menu using
    // the 'EditMenuDialog' component.
    isDisplayed: (env) => env.services.website.currentWebsite
        && env.services.website.currentWebsite.metadata.contentMenus
        && env.services.website.currentWebsite.metadata.contentMenus.length
        && !env.services.ui.isSmall,
});
