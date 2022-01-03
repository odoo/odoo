/** @odoo-module **/

import { NewContentModal, MODULE_STATUS } from '@website/systray_items/new_content';
import { patch } from 'web.utils';

patch(NewContentModal.prototype, 'website_blog_new_content', {
    setup() {
        this._super();
        this.state.newContentElements = this.state.newContentElements.map(element => {
            if (element.moduleXmlId === 'base.module_website_blog') {
                element.createNewContent = () => this.createNewBlogPost();
                element.status = MODULE_STATUS.INSTALLED;
            }
            return element;
        });
    },

    createNewBlogPost() {}
});
