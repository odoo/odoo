odoo.define('website_blog.website_blog', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.websiteBlog = publicWidget.Widget.extend({
    selector: '.website_blog',
    events: {
        'click #o_wblog_next_container': '_onNextBlogClick',
        'click #o_wblog_post_content_jump': '_onContentAnchorClick',
    },

    /**
     * @override
     */
    start: function () {
        $('.js_tweet, .js_comment').share({});
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onNextBlogClick: function (ev) {
        ev.preventDefault();
        var self = this;
        var $el = $(ev.currentTarget);
        var nexInfo = $el.find('#o_wblog_next_post_info').data();

        $el.css('height', $(window).height())
           .find('.o_record_cover_container').addClass(nexInfo.size + ' ' + nexInfo.text).end()
           .find('.o_wblog_toggle').toggleClass('d-none');

        // Use _.defer to calculate the 'offset()'' only after that size classes
        // have been applyed and that $el has been resized.
        _.defer(function () {
            self._forumScrollAction($el, 300, function () {
                window.location.href = nexInfo.url;
            });
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onContentAnchorClick: function (ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        var $el = $(ev.currentTarget.hash);

        this._forumScrollAction($el, 500, function () {
            window.location.hash = 'blog_content';
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onShareArticle: function (ev) {
        var url = '';
        var articleURL;
        ev.preventDefault();
        var $element = $(ev.currentTarget);
        if ($element.is('*[class*="_complete"]')) {
            var blogTitleComplete = encodeURIComponent($('#blog_post_name').html() || '');
            articleURL = encodeURIComponent(window.location.href);
            if ($element.hasClass('o_twitter_complete')) {
                url = 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=Amazing blog article : ' + blogTitleComplete + "! Check it live: " + articleURL;
            } else if ($element.hasClass('o_facebook_complete')) {
                url = 'https://www.facebook.com/sharer/sharer.php?u=' + articleURL;
            } else if ($element.hasClass('o_linkedin_complete')) {
                url = 'https://www.linkedin.com/shareArticle?mini=true&url=' + articleURL + '&title=' + blogTitleComplete;
            }
        } else {
            var blogPost = $element.parents('[name="blog_post"]');
            var blogPostTitle = encodeURIComponent(blogPost.find('.o_blog_post_title').html() || '');
            var blogArticleLink = blogPost.find('.o_blog_post_title').parent('a').attr('href');
            articleURL = encodeURIComponent(window.location.host + blogArticleLink);
            if ($element.hasClass('o_twitter')) {
                url = 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=Amazing blog article : ' + blogPostTitle + "! " + articleURL;
            } else if ($element.hasClass('o_facebook')) {
                url = 'https://www.facebook.com/sharer/sharer.php?u=' + articleURL;
            } else if ($element.hasClass('o_linkedin')) {
                url = 'https://www.linkedin.com/shareArticle?mini=true&url=' + articleURL + '&title=' + blogPostTitle;
            }
        }
        window.open(url, '', 'menubar=no, width=500, height=400');
    },

    //--------------------------------------------------------------------------
    // Utils
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {JQuery} $el - the element we are scrolling to
     * @param {Integer} duration - scroll animation duration
     * @param {Function} callback - to be executed after the scroll is performed
     */
    _forumScrollAction: function ($el, duration, callback) {
        var $mainNav = $('#wrapwrap > header');
        var gap = $mainNav.height() + $mainNav.offset().top;

        $('html, body').stop().animate({
            scrollTop: $el.offset().top - gap
        }, duration, 'swing', function () {
            callback();
        });
    },
});
});
