/** @odoo-module **/

import { registry } from "@web/core/registry";
import { DynamicSnippetOptions } from "@website/snippets/s_dynamic_snippet/options";
import {
    registerWebsiteOption,
} from "@website/js/editor/snippets.registry";


export class DynamicSnippetBlogPostsOptions extends DynamicSnippetOptions {
    /**
     * @override
     */
    async willStart() {
        this.blogs = await this._fetchBlogs();
        this.modelNameFilter = 'blog.post';
        await super.willStart(...arguments);
        this.renderContext.blogs = this.blogs;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     *
     * @override
     * @private
     */
    _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'hover_effect_opt') {
            return this.$target.get(0).dataset.templateKey === 'website_blog.dynamic_filter_template_blog_post_big_picture';
        }
        return super._computeWidgetVisibility(...arguments);
    }
    /**
     * Fetches blogs.
     * @private
     * @returns {Promise}
     */
    _fetchBlogs() {
        const websiteId = this.env.services.website.currentWebsite.id;
        const websiteDomain = ["|", ["website_id", "=", false], ["website_id", "=", websiteId]];
        return this.env.services.orm.searchRead("blog.blog", websiteDomain, ["id", "name"]);
    }
    /**
     * @override
     * @private
     */
    async _getRenderContext() {
        const renderContext = super._getRenderContext();
        renderContext.blogs = this.blogs;
        return renderContext;
    }
    /**
     * Sets default options values.
     * @override
     * @private
     */
    _setOptionsDefaultValues() {
        this._setOptionValue('filterByBlogId', -1);
        super._setOptionsDefaultValues(...arguments);
    }
}

registerWebsiteOption("DynamicSnippetBlogPostsOptions", {
    Class: DynamicSnippetBlogPostsOptions,
    template: "website_blog.s_blog_posts_option",
    selector: ".s_dynamic_snippet_blog_posts, .s_blog_posts",
});

const anchorOption = registry.category("snippet_options").get("Anchor");
anchorOption.exclude += ",.o_wblog_post_content_field > :not(div, section)";
registry.category("snippet_options").add("Anchor", anchorOption, {
    force: true,
});
