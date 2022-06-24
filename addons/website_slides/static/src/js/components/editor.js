/** @odoo-module **/

import { WebsiteEditorComponent } from '@website/components/editor/editor';
import { patch } from 'web.utils';

patch(WebsiteEditorComponent.prototype, 'website_slides_editor', {
    /**
     * @override
     */
    publicRootReady() {
        const { pathname, search } = this.websiteService.contentWindow.location;
        if (pathname.includes('slides') && search.includes('fullscreen=1')) {
            this.websiteContext.edition = false;
            this.websiteService.goToWebsite({path: `${pathname}?fullscreen=0`, edition: true});
        } else {
            this._super(...arguments);
        }
    }
});
