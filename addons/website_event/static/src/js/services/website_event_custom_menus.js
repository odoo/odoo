import { registry } from '@web/core/registry';
import { EditMenuDialog } from '@website/components/dialog/edit_menu';

class CustomEditMenuDialog extends EditMenuDialog {
    /**
     * override the addMenu method to handle event page URLs
     * @override
     */
    addMenu(isMegaMenu, customUrl) {
        let eventPagePrefix = customUrl;
        const websiteMetadata = this.website.currentWebsite.metadata;
        if (websiteMetadata.mainObject?.model === "event.event") {
            const path = new URL(websiteMetadata.path);
            eventPagePrefix = `/event/${path.pathname.split("/")[2]}/page`;
        }
        super.addMenu(isMegaMenu, eventPagePrefix);
    }
}

registry.category('website_custom_menus').add('website.custom_menu_edit_menu', {
    Component: CustomEditMenuDialog,
    isDisplayed: (env) => env.services.website.currentWebsite
        && env.services.website.currentWebsite.metadata.contentMenus
        && env.services.website.currentWebsite.metadata.contentMenus.length,
}, { force: true });
