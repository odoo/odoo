import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class DynamicSnippetBlogPostsOptionPlugin extends Plugin {
    static id = "dynamicSnippetBlogPostsOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        model_name_filter_overrides: (snippetEl) => {
            if (snippetEl.matches(".s_dynamic_snippet_blog_posts, .s_blog_posts_carousel")) {
                return "blog.post";
            }
        },
    };
}

registry
    .category("website-plugins")
    .add(DynamicSnippetBlogPostsOptionPlugin.id, DynamicSnippetBlogPostsOptionPlugin);
