import { NewContentModal, MODULE_STATUS } from '@website/systray_items/new_content';
import { patch } from "@web/core/utils/patch";

patch(NewContentModal.prototype, {
    setup() {
        super.setup();

        const newBlogElement = this.state.newContentElements.find(element => element.moduleXmlId === 'base.module_website_blog');
        const isBlogPage = window.location.pathname === "/blog";
        let context = undefined;

        if (!isBlogPage) {
            const iframe = document.querySelector("iframe.o_iframe");
            const blogEl = iframe?.contentDocument?.querySelector(
                "main #wrap.website_blog [data-oe-model='blog.blog']"
            );
            const blogId = blogEl ? parseInt(blogEl.dataset.oeId) : undefined;

            if (blogId) {
                context = { default_blog_id: blogId };
            }
        }
        newBlogElement.createNewContent = () => this.onAddContent("website_blog.blog_post_action_add", true, context);
        newBlogElement.status = MODULE_STATUS.INSTALLED;
        newBlogElement.model = 'blog.post';
    },
});
