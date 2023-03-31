/** @odoo-module alias=website_blog.s_blog_posts_frontend **/

import publicWidget from "web.public.widget";
import DynamicSnippet from "website.s_dynamic_snippet";

const DynamicSnippetBlogPosts = DynamicSnippet.extend({
    selector: '.s_dynamic_snippet_blog_posts',
    disabledInEditableMode: false,

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Method to be overridden in child components in order to provide a search
     * domain if needed.
     * @override
     * @private
     */
    _getSearchDomain: function () {
        const searchDomain = this._super.apply(this, arguments);
        const filterByBlogId = parseInt(this.$el.get(0).dataset.filterByBlogId);
        if (filterByBlogId >= 0) {
            searchDomain.push(['blog_id', '=', filterByBlogId]);
        }
        return searchDomain;
    },

});
publicWidget.registry.blog_posts = DynamicSnippetBlogPosts;

export default DynamicSnippetBlogPosts;
