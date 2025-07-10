import {
    NewContentSystrayItem,
    MODULE_STATUS,
} from "@website/client_actions/website_preview/new_content_systray_item";
import { patch } from "@web/core/utils/patch";

patch(NewContentSystrayItem.prototype, {
    setup() {
        super.setup();

        const newBlogElement = this.state.newContentElements.find(
            (element) => element.moduleXmlId === "base.module_website_blog"
        );
        newBlogElement.createNewContent = () =>
            this.onAddContent(
                "website_blog.blog_post_action_add",
                true,
                this.getCurrentBlogContext()
            );
        newBlogElement.status = MODULE_STATUS.INSTALLED;
        newBlogElement.model = "blog.post";
    },

    getCurrentBlogContext() {
        // Using iframe to access mainObject to check if we are on blog page
        const iframeEl = document.querySelector("iframe").contentDocument;
        const isBlogPage = iframeEl.documentElement.dataset.mainObject?.startsWith("blog");

        if (isBlogPage) {
            const blogEl = iframeEl.querySelector("#wrap.website_blog [data-oe-model='blog.blog']");
            const blogId = parseInt(blogEl?.dataset.oeId);

            if (blogId) {
                return { default_blog_id: blogId };
            }
        }
        return null;
    },
});
