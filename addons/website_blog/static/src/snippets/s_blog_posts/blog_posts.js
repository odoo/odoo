import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";

export class BlogPosts extends DynamicSnippet {
    static selector = ".s_dynamic_snippet_blog_posts";

    /**
     * @override
     */
    getSearchDomain() {
        const searchDomain = super.getSearchDomain(...arguments);
        const filterByBlogId = parseInt(this.el.dataset.filterByBlogId);
        const filterByTagId = parseInt(this.el.dataset.filterByTagId);
        const filterByAuthorId = parseInt(this.el.dataset.filterByAuthorId);
        if (filterByBlogId >= 0) {
            searchDomain.push(["blog_id", "=", filterByBlogId]);
        }
        if (filterByTagId >= 0) {
            searchDomain.push(["tag_ids", "=", filterByTagId]);
        }
        if (filterByAuthorId >= 0) {
            searchDomain.push(["author_id", "=", filterByAuthorId]);
        }
        return searchDomain;
    }
}

registry
    .category("public.interactions")
    .add("website_blog.blog_posts", BlogPosts);

registry
    .category("public.interactions.edit")
    .add("website_blog.blog_posts", {
        Interaction: BlogPosts,
    });
