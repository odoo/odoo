/** @odoo-module **/

import { EditInBackendSystray } from '@website/systray_items/edit_in_backend';
import { patch } from 'web.utils';
import wUtils from 'website.utils';

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
        wUtils.sendRequest('/blog/post_duplicate', { blog_post_id: mainObject.id });
    }
});
