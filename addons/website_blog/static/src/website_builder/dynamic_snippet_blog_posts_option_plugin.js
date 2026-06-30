import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class DynamicSnippetBlogPostsOptionPlugin extends Plugin {
    static id = "dynamicSnippetBlogPostsOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dynamic_filter_search_domain_processors: (
            domain,
            { blogByIds, blogByTagIds, blogByAuthorIds }
        ) => {
            if (blogByIds?.length) {
                domain.push(["blog_id", "in", blogByIds.map((e) => e.id)]);
            }
            if (blogByTagIds?.length) {
                domain.push(["tag_ids", "in", blogByTagIds.map((e) => e.id)]);
            }
            if (blogByAuthorIds?.length) {
                domain.push(["author_id", "in", blogByAuthorIds.map((e) => e.id)]);
            }
            return domain;
        },
        model_name_filter_overrides: (snippetEl) => {
            if (snippetEl.matches(".s_dynamic_snippet_blog_posts")) {
                return "blog.post";
            }
        },
    };
}

registry
    .category("website-plugins")
    .add(DynamicSnippetBlogPostsOptionPlugin.id, DynamicSnippetBlogPostsOptionPlugin);
