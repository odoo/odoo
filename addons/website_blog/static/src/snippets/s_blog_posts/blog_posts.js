import { registry } from "@web/core/registry";
import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";

export class DynamicSnippetBlogPosts extends DynamicSnippet {
    static selector = ".s_dynamic_snippet_blog_posts";

    /**
     * Method to be overridden in child components in order to provide a search
     * domain if needed.
     * @override
     */
    getSearchDomain() {
        const searchDomain = super.getSearchDomain(...arguments);
        const filterByBlogId = parseInt(this.el.dataset.filterByBlogId);
        if (filterByBlogId >= 0) {
            searchDomain.push(["blog_id", "=", filterByBlogId]);
        }
        return searchDomain;
    }
    /**
     * @override
     */
    getMainPageUrl() {
        return "/blog";
    }
}

registry.category("public.interactions").add("website_blog.blog_posts", DynamicSnippetBlogPosts);

registry
    .category("public.interactions.edit")
    .add("website_blog.blog_posts", {
        Interaction: DynamicSnippetBlogPosts,
    });
