import { registry } from "@web/core/registry";
import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/000";

export class DynamicSnippetBlogPosts extends DynamicSnippet {
    static selector = ".s_dynamic_snippet_blog_posts";
    // TODO Support edit mode.
    static disabledInEditableMode = false;

    /**
     * Method to be overridden in child components in order to provide a search
     * domain if needed.
     * @override
     */
    getSearchDomain() {
        const searchDomain = super.getSearchDomain(...arguments);
        const filterByBlogId = parseInt(this.el.dataset.filterByBlogId);
        if (filterByBlogId >= 0) {
            searchDomain.push(['blog_id', '=', filterByBlogId]);
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

registry.category("website.active_elements").add("website_blog.blog_posts", DynamicSnippetBlogPosts);
