import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";

export class BlogPosts extends DynamicSnippet {
    static selector = ".s_dynamic_snippet_blog_posts";

    /**
     * @override
     */
    getSearchDomain() {
        const searchDomain = super.getSearchDomain(...arguments);

        const getParsedIds = (key) => {
            return this.el.dataset[key]
                ? JSON.parse(this.el.dataset[key]).map((t) => t.id)
                : [];
        };

        const filterByTagIds = getParsedIds("filterByTagIds");
        const filterByBlogIds = getParsedIds("filterByBlogIds");
        const filterByAuthorIds = getParsedIds("filterByAuthorIds");

        if (filterByBlogIds.length) {
            searchDomain.push(["blog_id", "in", filterByBlogIds]);
        }
        if (filterByTagIds.length) {
            searchDomain.push(["tag_ids", "in", filterByTagIds]);
        }
        if (filterByAuthorIds.length) {
            searchDomain.push(["author_id", "in", filterByAuthorIds]);
        }
        return searchDomain;
    }
}

registry.category("public.interactions").add("website_blog.blog_posts", BlogPosts);

registry.category("public.interactions.edit").add("website_blog.blog_posts", {
    Interaction: BlogPosts,
});
