/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";
import dynamicSnippetOptions from "@website/snippets/s_dynamic_snippet/options";

import wUtils from "@website/js/utils";

const dynamicSnippetBlogPostsOptions = dynamicSnippetOptions.extend({
    /**
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.modelNameFilter = 'blog.post';
        this.blogs = {};
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     *
     * @override
     * @private
     */
    _computeWidgetVisibility: function (widgetName, params) {
        const templateKey = this.$target.get(0).dataset.templateKey;

        if (widgetName === 'hover_effect_opt') {
            return templateKey === 'website_blog.dynamic_filter_template_blog_post_big_picture';
        } else if (widgetName === 'picture_size_opt') {
            return templateKey === 'website_blog.dynamic_filter_template_blog_post_big_picture' ||
            templateKey === 'website_blog.dynamic_filter_template_blog_post_horizontal' ||
            templateKey === 'website_blog.dynamic_filter_template_blog_post_card';
        } else if (widgetName === 'teaser_opt') {
            return templateKey === 'website_blog.dynamic_filter_template_blog_post_card' ||
            templateKey === 'website_blog.dynamic_filter_template_blog_post_list';
        } else if (widgetName === 'date_opt') {
            return templateKey === 'website_blog.dynamic_filter_template_blog_post_card' ||
            templateKey === 'website_blog.dynamic_filter_template_blog_post_horizontal' ||
            templateKey === 'website_blog.dynamic_filter_template_blog_post_list';
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Fetches blogs.
     * @private
     * @returns {Promise}
     */
    _fetchBlogs: function () {
        return this.orm.searchRead("blog.blog", wUtils.websiteDomain(this), ["id", "name"]);
    },
    /**
     *
     * @override
     * @private
     */
    _renderCustomXML: async function (uiFragment) {
        await this._super.apply(this, arguments);
        await this._renderBlogSelector(uiFragment);
    },
    /**
     * Renders the blog option selector content into the provided uiFragment.
     * @private
     * @param {HTMLElement} uiFragment
     */
    _renderBlogSelector: async function (uiFragment) {
        if (!Object.keys(this.blogs).length) {
            const blogsList = await this._fetchBlogs();
            this.blogs = {};
            for (let index in blogsList) {
                this.blogs[blogsList[index].id] = blogsList[index];
            }
        }
        const blogSelectorEl = uiFragment.querySelector('[data-name="blog_opt"]');
        return this._renderSelectUserValueWidgetButtons(blogSelectorEl, this.blogs);
    },
    /**
     * Sets default options values.
     * @override
     * @private
     */
    _setOptionsDefaultValues: function () {
        this._setOptionValue('filterByBlogId', -1);
        this._super.apply(this, arguments);
    },
});

options.registry.dynamic_snippet_blog_posts = dynamicSnippetBlogPostsOptions;

export default dynamicSnippetBlogPostsOptions;
