import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class BlogPostTitlePlugin extends Plugin {
    static id = "blogPostTitle";
    resources = {
        before_setup_editor_handlers: () => {
            // TODO: Remove in master and modify the XML
            // view addons/website_blog/views/website_blog_templates.xml for the
            // two templates (opt_blog_cover_post_fullwidth_design,
            // opt_blog_cover_post)
            const latestPostsEl = this.editable.querySelector(
                "#o_wblog_blog_top .h1.o_not_editable"
            );
            latestPostsEl?.classList.remove("o_not_editable");
        },
    };
}

registry.category("website-plugins").add(BlogPostTitlePlugin.id, BlogPostTitlePlugin);
registry.category("website-translation-plugins").add(BlogPostTitlePlugin.id, BlogPostTitlePlugin);
