/** @odoo-module  */

import { registry } from '@web/core/registry';
import { EditMenuDialog } from '@website/components/dialog/edit_menu';

registry.category('website_custom_menus').add('website_event.menu_edit_menu', {
    Component: EditMenuDialog,
    isDisplayed: (env) => env.services.website.currentWebsite
        && env.services.website.currentWebsite.metadata.contentMenuId
        && !env.services.ui.isSmall,
    getProps: (services) => ({
        rootID: parseInt(services.website.currentWebsite.metadata.contentMenuId, 10),
    }),
});
