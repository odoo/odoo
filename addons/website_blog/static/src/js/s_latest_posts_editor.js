odoo.define('website_blog.s_latest_posts_editor', function (require) {
'use strict';

var core = require('web.core');
var sOptions = require('web_editor.snippets.options');

var _t = core._t;

sOptions.registry.js_get_posts_limit = sOptions.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    postsLimit: function (previewMode, value, $opt) {
        value = parseInt(value);
        this.$target.attr('data-posts-limit', value).data('postsLimit', value);
        this.trigger_up('animation_start_demand', {
            editableMode: true,
            $target: this.$target,
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _setActive: function () {
        var self = this;
        this._super.apply(this, arguments);
        this.$('[data-posts-limit]').addBack('[data-posts-limit]')
            .removeClass('active')
            .filter(function () {
                return (self.$target.data('postsLimit') || 3) == $(this).data('postsLimit');
            })
            .addClass('active');
    },
});

sOptions.registry.js_get_posts_selectBlog = sOptions.Class.extend({
    /**
     * @override
     */
    start: function () {
        var self = this;

        var def = this._rpc({
            model: 'blog.blog',
            method: 'search_read',
            args: [[], ['name', 'id']],
        }).then(function (blogs) {
            var $menu = self.$el.find('[data-filter-by-blog-id="0"]').parent();
            _.each(blogs, function (blog) {
                $menu.append($('<a/>', {
                    class: 'dropdown-item',
                    'data-filter-by-blog-id': blog.id,
                    'data-no-preview': 'true',
                    text: blog.name,
                }));
            });
        });

        return $.when(this._super.apply(this, arguments), def);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    filterByBlogId: function (previewMode, value, $opt) {
        value = parseInt(value);
        this.$target.attr('data-filter-by-blog-id', value).data('filterByBlogId', value);
        this.trigger_up('animation_start_demand', {
            editableMode: true,
            $target: this.$target,
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _setActive: function () {
        var self = this;
        this._super.apply(this, arguments);
        this.$('[data-filter-by-blog-id]').addBack('[data-filter-by-blog-id]')
            .removeClass('active')
            .filter(function () {
                return (self.$target.data('filterByBlogId') || 0) == $(this).data('filterByBlogId');
            })
            .addClass('active');
    },
});
});
