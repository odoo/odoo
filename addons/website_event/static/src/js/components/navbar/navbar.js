/** @odoo-module  */

import { patch } from 'web.utils';
import { NavBar } from '@web/webclient/navbar/navbar';
import { EditMenuDialog } from '@website/components/dialog/edit_menu';

const { onWillStart } = owl;

patch(NavBar.prototype, 'website_events_navbar', {
    setup() {
        this._super();

        onWillStart(() => {
            this.websiteEditingMenus['website_event.menu_edit_menu'] = {
                Component: EditMenuDialog,
                isDisplayed: () => this.websiteService.currentWebsite && this.websiteService.currentWebsite.metadata.contentMenuId,
                getProps: () => ({
                    rootID: parseInt(this.websiteService.currentWebsite.metadata.contentMenuId, 10),
                }),
            };
        });
    },
});
