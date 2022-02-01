/** @odoo-module **/

import { EditInBackendSystray } from '@website/systray_items/edit_in_backend';
import { patch } from 'web.utils';

patch(EditInBackendSystray.prototype, 'website_blog_edit_in_backend', {
    /**
     * @override
     */
    getElements() {
        const elements = this._super();
        const { metadata: { mainObject } } = this.websiteService.currentWebsite;
        if (mainObject.model === 'blog.post') {
            return [...elements, {
                title: this.env._t("Duplicate"),
                callback: () => this.duplicate(),
            }];
        }
        return elements;
    },

    async duplicate() {
        const { metadata: { mainObject } } = this.websiteService.currentWebsite;
        const duplicateUrl = await this.websiteService.sendRequest('/blog/post_duplicate', { blog_post_id: mainObject.id });
        this.websiteService.goToWebsite({ path: duplicateUrl });
    }
});
