odoo.define('website_blog.new_blog_post', function (require) {
'use strict';

var core = require('web.core');
var wUtils = require('website.utils');
var WebsiteNewMenu = require('website.newMenu');

var _t = core._t;

WebsiteNewMenu.include({
    actions: _.extend({}, WebsiteNewMenu.prototype.actions || {}, {
        new_blog_post: '_createNewBlogPost',
    }),

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Asks the user information about a new blog post to create, then creates
     * it and redirects the user to this new post.
     *
     * @private
     * @returns {Promise} Unresolved if there is a redirection
     */
    _createNewBlogPost: function () {
        return this._rpc({
            model: 'blog.blog',
            method: 'search_read',
            args: [wUtils.websiteDomain(this), ['name']],
        }).then(function (blogs) {
            if (blogs.length === 1) {
                document.location = '/blog/' + blogs[0]['id'] + '/post/new';
                return new Promise(function () {});
            } else if (blogs.length > 1) {
                return wUtils.prompt({
                    id: 'editor_new_blog',
                    window_title: _t("New Blog Post"),
                    select: _t("Select Blog"),
                    init: function (field) {
                        return _.map(blogs, function (blog) {
                            return [blog['id'], blog['name']];
                        });
                    },
                }).then(function (result) {
                    var blog_id = result.val;
                    if (!blog_id) {
                        return;
                    }
                    document.location = '/blog/' + blog_id + '/post/new';
                    return new Promise(function () {});
                });
            }
        });
    },
});
});
