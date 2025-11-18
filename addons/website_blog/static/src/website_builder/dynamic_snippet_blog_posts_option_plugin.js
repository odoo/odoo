import { DYNAMIC_SNIPPET_CAROUSEL } from "@website/builder/plugins/options/dynamic_snippet_carousel_option_plugin";
import { setDatasetIfUndefined } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
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
    static dependencies = ["dynamicSnippetCarouselOption"];
    static shared = ["fetchBlogs", "getModelNameFilter"];
    modelNameFilter = "blog.post";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: withSequence(DYNAMIC_SNIPPET_CAROUSEL, DynamicSnippetBlogPostsOption),
        dynamic_snippet_template_updated: this.onTemplateUpdated.bind(this),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };
    setup() {
        this.blogs = undefined;
    }
    getModelNameFilter() {
        return this.modelNameFilter;
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(DynamicSnippetBlogPostsOption.selector)) {
            setDatasetIfUndefined(snippetEl, "filterByBlogId", -1);
            await this.dependencies.dynamicSnippetCarouselOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter
            );
        }
    }
    onTemplateUpdated({ el, template }) {
        if (el.matches(DynamicSnippetBlogPostsOption.selector)) {
            this.dependencies.dynamicSnippetCarouselOption.updateTemplateSnippetCarousel(
                el,
                template
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
