odoo.define('website_blog.s_latest_posts_editor', function (require) {
'use strict';

var core = require('web.core');
var sOptions = require('web_editor.snippets.options');
var wUtils = require('website.utils');

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
        this.trigger_up('widgets_start_request', {
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
        this._super.apply(this, arguments);
        var activeLimit = this.$target.data('postsLimit') || 3;

        this.$el.find('[data-posts-limit]').removeClass('active');
        this.$el.find('[data-posts-limit=' + activeLimit + ']').addClass('active');
    },
});

sOptions.registry.js_get_posts_selectBlog = sOptions.Class.extend({
    /**
     * @override
     */
    start: function () {
        var def = this._rpc({
            model: 'blog.blog',
            method: 'search_read',
            args: [wUtils.websiteDomain(this), ['name']],
        }).then(blogs => {
            var allBlogsEl = this.el.querySelector('[data-filter-by-blog-id="0"]');
            var menuEl = allBlogsEl.parentNode;
            for (const blog of blogs) {
                let el = allBlogsEl.cloneNode();
                el.dataset.filterByBlogId = blog.id;
                el.textContent = blog.name;
                menuEl.appendChild(el);
            }
            this._setActive();
        });

        return Promise.all([this._super.apply(this, arguments), def]);
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
        this.trigger_up('widgets_start_request', {
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
        this._super.apply(this, arguments);

        var activeBlogId = this.$target.data('filterByBlogId') || 0;

        this.$el.find('[data-filter-by-blog-id]').removeClass('active');
        this.$el.find('[data-filter-by-blog-id=' + activeBlogId + ']').addClass('active');
    },
});
});
