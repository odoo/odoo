odoo.define('website_blog.s_latest_posts_frontend', function (require) {
'use strict';

var core = require('web.core');
var wUtils = require('website.utils');
var publicWidget = require('web.public.widget');

var _t = core._t;

publicWidget.registry.js_get_posts = publicWidget.Widget.extend({
    selector: '.js_get_posts',
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        var self = this;
        var limit = self.$target.data('postsLimit') || 3;
        var blogID = self.$target.data('filterByBlogId');
        var template = self.$target.data('template') || 'website_blog.s_latest_posts_list_template';
        var loading = self.$target.data('loading');

        this.$target.empty(); // Compatibility with db that saved content inside by mistake
        this.$target.attr('contenteditable', 'False'); // Prevent user edition

        var domain = [
            ['website_published', '=', true],
            ['post_date', '<=', moment().utc().locale('en').format('YYYY-MM-DD HH:mm:ss')],
        ];
        if (blogID) {
            domain.push(['blog_id', '=', parseInt(blogID)]);
        }

        var prom = new Promise(function (resolve) {
            self._rpc({
                route: '/blog/render_latest_posts',
                params: {
                    template: template,
                    domain: domain,
                    limit: limit,
                },
            }).then(function (posts) {
                var $posts = $(posts).filter('.s_latest_posts_post');
                if (!$posts.length) {
                    self.$target.append($('<div/>', {class: 'col-md-6 offset-md-3'})
                    .append($('<div/>', {
                        class: 'alert alert-warning alert-dismissible text-center',
                        text: _t("No blog post was found. Make sure your posts are published."),
                    })));
                    return;
                }

                if (loading && loading === true) {
                    // Perform an intro animation
                    self._showLoading($posts);
                } else {
                    self.$target.html($posts);
                }
                resolve();
            }).guardedCatch(function () {
                if (self.editableMode) {
                    self.$target.append($('<p/>', {
                        class: 'text-danger',
                        text: _t("An error occured with this latest posts block. If the problem persists, please consider deleting it and adding a new one"),
                    }));
                }
                resolve();
            });
        });
        return Promise.all([this._super.apply(this, arguments), prom]);
    },
    /**
     * @override
     */
    destroy: function () {
        this.$target.empty();
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _showLoading: function ($posts) {
        var self = this;

        _.each($posts, function (post, i) {
            var $post = $(post);
            var $progress = $post.find('.s_latest_posts_loader');
            var bgUrl = $post.find('.o_record_cover_image').css('background-image').replace('url(','').replace(')','').replace(/\"/gi, "") || 'none';

            // Append $post to the snippet, regardless by the loading state.
            $post.appendTo(self.$target);

            // No cover-image found. Add a 'flag' class and exit.
            if (bgUrl === 'none') {
                $post.addClass('s_latest_posts_loader_no_cover');
                $progress.remove();
                return;
            }

            // Cover image found. Show the spinning icon.
            $progress.find('> div').removeClass('d-none').css('animation-delay', i * 200 + 'ms');
            var $dummyImg = $('<img/>', {src: bgUrl});

            // If the image is not loaded in 10 sec, remove loader and provide a fallback bg-color to the container.
            // Hopefully one day the image will load, covering the bg-color...
            var timer = setTimeout(function () {
                $post.find('.o_record_cover_image').addClass('bg-200');
                $progress.remove();
            }, 10000);

            wUtils.onceAllImagesLoaded($dummyImg).then(function () {
                $progress.fadeOut(500, function () {
                    $progress.removeClass('d-flex');
                });

                $dummyImg.remove();
                clearTimeout(timer);
            });
        });
    },
});
});
