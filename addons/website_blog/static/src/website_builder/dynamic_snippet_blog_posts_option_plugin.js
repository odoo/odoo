import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * @typedef { Object } DynamicSnippetBlogPostsOptionShared
 * @property { DynamicSnippetBlogPostsOptionPlugin['getModelNameFilter'] } getModelNameFilter
 */

export class DynamicSnippetBlogPostsOptionPlugin extends Plugin {
    static id = "dynamicSnippetBlogPostsOption";
    static dependencies = ["dynamicSnippetCarouselOption", "dynamicSnippetOption"];
    static shared = ["getModelNameFilter"];
    modelNameFilter = "blog.post";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };
    getModelNameFilter() {
        return this.modelNameFilter;
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_dynamic_snippet_blog_posts, .s_blog_posts_carousel")) {
            const optionKey = snippetEl.matches(".s_dynamic_snippet_blog_posts")
                ? "dynamicSnippetOption"
                : "dynamicSnippetCarouselOption";
            await this.dependencies[optionKey].setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter
            );
        }
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetBlogPostsOptionPlugin.id, DynamicSnippetBlogPostsOptionPlugin);
