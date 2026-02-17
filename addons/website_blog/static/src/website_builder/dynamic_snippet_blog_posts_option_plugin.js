import { setDatasetIfUndefined } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * @typedef { Object } DynamicSnippetBlogPostsOptionShared
 * @property { DynamicSnippetBlogPostsOptionPlugin['fetchBlogs'] } fetchBlogs
 * @property { DynamicSnippetBlogPostsOptionPlugin['getModelNameFilter'] } getModelNameFilter
 */

export class DynamicSnippetBlogPostsOptionPlugin extends Plugin {
    static id = "dynamicSnippetBlogPostsOption";
    static dependencies = ["dynamicSnippetOption"];
    static shared = ["fetchBlogs", "getModelNameFilter"];
    modelNameFilter = "blog.post";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };
    setup() {
        this.blogs = undefined;
    }
    getModelNameFilter() {
        return this.modelNameFilter;
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_dynamic_snippet_blog_posts")) {
            setDatasetIfUndefined(snippetEl, "filterByBlogId", -1);
            await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter
            );
        }
    }
    async fetchBlogs() {
        if (!this.blogs) {
            this.blogs = this._fetchBlogs();
        }
        return this.blogs;
    }
    async _fetchBlogs() {
        // TODO put in an utility function
        const websiteDomain = [
            "|",
            ["website_id", "=", false],
            ["website_id", "=", this.services.website.currentWebsite.id],
        ];
        return this.services.orm.searchRead("blog.blog", websiteDomain, ["id", "name"]);
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetBlogPostsOptionPlugin.id, DynamicSnippetBlogPostsOptionPlugin);
