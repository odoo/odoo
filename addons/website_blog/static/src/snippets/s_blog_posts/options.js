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
        const templateKeyPrefix = "website_blog.dynamic_filter_template_blog_post_";
        const templateKey = this.$target[0].dataset.templateKey?.replace(templateKeyPrefix, "");
        const templatesWidgetVisibility = {
            hover_effect_opt: ["big_picture"],
            picture_size_opt: ["big_picture", "horizontal", "card"],
            teaser_opt: ["card", "list"],
            date_opt: [
                "card",
                "horizontal",
                "list",
                "single_full",
                "single_aside",
                "single_circle",
            ],
        };
        if (widgetName in templatesWidgetVisibility) {
            return templatesWidgetVisibility[widgetName].includes(templateKey);
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
