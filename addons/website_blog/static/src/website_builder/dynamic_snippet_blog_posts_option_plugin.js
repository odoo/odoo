import {
    DYNAMIC_SNIPPET,
    setDatasetIfUndefined,
} from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { DynamicSnippetBlogPostsOption } from "./dynamic_snippet_blog_posts_option";

/**
 * @typedef { Object } DynamicSnippetBlogPostsOptionShared
 * @property { DynamicSnippetBlogPostsOptionPlugin['fetchBlogs'] } fetchBlogs
 * @property { DynamicSnippetBlogPostsOptionPlugin['getModelNameFilter'] } getModelNameFilter
 */

class DynamicSnippetBlogPostsOptionPlugin extends Plugin {
    static id = "dynamicSnippetBlogPostsOption";
    static dependencies = ["dynamicSnippetOption"];
    static shared = ["fetchAuthors", "getModelNameFilter"];
    modelNameFilter = "blog.post";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: withSequence(DYNAMIC_SNIPPET, DynamicSnippetBlogPostsOption),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };
    setup() {
        this.authors = undefined;
    }
    getModelNameFilter() {
        return this.modelNameFilter;
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(DynamicSnippetBlogPostsOption.selector)) {
            setDatasetIfUndefined(snippetEl, "filterByAuthorId", -1);
            await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter
            );
        }
    }

    async fetchAuthors(snippetEl) {
        const websiteDomain = this._websiteDomain();
        let domain = [...websiteDomain];

        if (snippetEl) {
            const tags = snippetEl.dataset.filterByTagIds
                ? JSON.parse(snippetEl.dataset.filterByTagIds)
                : [];
            const blogs = snippetEl.dataset.filterByBlogIds
                ? JSON.parse(snippetEl.dataset.filterByBlogIds)
                : [];

            const tagIds = tags.map((t) => t.id);
            const blogIds = blogs.map((b) => b.id);

            const isFiltered = tagIds.length || blogIds.length;

            // Apply filters if present
            if (tagIds.length) {
                domain.push(["tag_ids", "in", tagIds]);
            }

            if (blogIds.length) {
                domain.push(["blog_id", "in", blogIds]);
            }

            // Cache only unfiltered case
            if (isFiltered || !this.authors) {
                this.authors = await this.services.orm
                    .formattedReadGroup("blog.post", domain, ["author_id"], [])
                    .then((results) =>
                        results.map((r) => ({
                            label: r.author_id[1],
                            value: {
                                id: r.author_id[0],
                                name: r.author_id[1],
                            },
                        })),
                    );
            }
        }
        return this.authors;
    }

    _websiteDomain() {
        const websiteId = this.services.website.currentWebsite.id;
        return ["|", ["website_id", "=", false], ["website_id", "=", websiteId]];
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetBlogPostsOptionPlugin.id, DynamicSnippetBlogPostsOptionPlugin);
