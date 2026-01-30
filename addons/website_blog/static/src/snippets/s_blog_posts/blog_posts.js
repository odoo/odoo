import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";
import { groupBy } from "@web/core/utils/arrays";

export class BlogPosts extends DynamicSnippet {
    static selector = ".s_dynamic_snippet_blog_posts";

    /**
     * @override
     */
    getSearchDomain() {
        const searchDomain = super.getSearchDomain(...arguments);
        const filterByBlogId = parseInt(this.el.dataset.filterByBlogId);
        if (filterByBlogId >= 0) {
            searchDomain.push(["blog_id", "=", filterByBlogId]);
        }
        const filterByTagIds = this.el.dataset.filterByTagIds;
        if (filterByTagIds) {
            const tagGroupedByCategory = groupBy(JSON.parse(filterByTagIds), "category_id");
            for (const category in tagGroupedByCategory) {
                searchDomain.push([
                    "tag_ids",
                    "in",
                    tagGroupedByCategory[category].map((e) => e.id),
                ]);
            }
        }
        return searchDomain;
    }
}

registry.category("public.interactions").add("website_blog.blog_posts", BlogPosts);

registry.category("public.interactions.edit").add("website_blog.blog_posts", {
    Interaction: BlogPosts,
});
