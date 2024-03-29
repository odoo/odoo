/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import DynamicSnippet from "@website/snippets/s_dynamic_snippet/000";

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
