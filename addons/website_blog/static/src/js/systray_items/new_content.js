/** @odoo-module **/

import { NewContentModal, MODULE_STATUS } from '@website/systray_items/new_content';
import { patch } from "@web/core/utils/patch";

patch(NewContentModal.prototype, {
    setup() {
        super.setup();

        const newBlogElement = this.state.newContentElements.find(element => element.moduleXmlId === 'base.module_website_blog');
        newBlogElement.createNewContent = () => this.onAddContent('website_blog.blog_post_action_add', true);
        newBlogElement.status = MODULE_STATUS.INSTALLED;
        newBlogElement.model = 'blog.post';
    },
});
