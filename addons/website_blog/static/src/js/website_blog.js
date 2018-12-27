odoo.define('website_blog.website_blog', function (require) {
'use strict';

var sAnimations = require('website.content.snippets.animation');

sAnimations.registry.websiteBlog = sAnimations.Class.extend({
    selector: '.website_blog',
    read_events: {
        'click .cover_footer': '_onNextBlogClick',
        'click a[href^="#blog_content"]': '_onContentAnchorClick',
        'click .o_twitter, .o_facebook, .o_linkedin, .o_google, .o_twitter_complete, .o_facebook_complete, .o_linkedin_complete, .o_google_complete': '_onShareArticle',
        'click .blog_post_year_collapse': '_onYearCollapseClick',
        'mouseenter div.o_blog_post_complete a': '_onBlogPostMouseEnter',
        'mouseleave div.o_blog_post_complete a': '_onBlogPostMouseLeave',
    },

    /**
     * @override
     */
    start: function () {
        $('.js_tweet, .js_comment').share({});

        // Active year collapse
        var $activeYear = $('.blog_post_year li.active');
        if ($activeYear.length) {
            var id = $activeYear.closest('ul').attr('id');
            this._toggleYearCollapse($('.blog_post_year_collapse[data-target="#' + id + '"]'));
        }

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {jQuery} $el
     */
    _toggleYearCollapse: function ($el) {
        $el.find('i.fa').toggleClass('fa-chevron-down fa-chevron-right');
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
        var $el = $(ev.currentTarget);
        var newLocation = $('.js_next')[0].href;
        var top = $el.offset().top;
        $el.animate({
            height: $(window).height() + 'px',
        }, 300);
        $('html, body').animate({
            scrollTop: top,
        }, 300, 'swing', function () {
           window.location.href = newLocation;
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onContentAnchorClick: function (ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        var element = ev.currentTarget;
        var target = $(element.hash);
        $('html, body').stop().animate({
            scrollTop: target.offset().top - 32,
        }, 500, 'swing', function () {
            window.location.hash = 'blog_content';
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onShareArticle: function (ev) {
        var url = '';
        var $element = $(ev.currentTarget);
        if ($element.is('*[class*="_complete"]')) {
            var blogTitleComplete = $('#blog_post_name').html() || '';
            if ($element.hasClass('o_twitter_complete')) {
                url = 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=Amazing blog article : ' + blogTitleComplete + "! Check it live: " + window.location.href;
            } else if ($element.hasClass('o_facebook_complete')) {
                url = 'https://www.facebook.com/sharer/sharer.php?u=' + window.location.href;
            } else if ($element.hasClass('o_linkedin_complete')) {
                url = 'https://www.linkedin.com/shareArticle?mini=true&url=' + window.location.href + '&title=' + blogTitleComplete;
            } else {
                url = 'https://plus.google.com/share?url=' + window.location.href;
            }
        } else {
            var blogPost = $element.parents('[name="blogPost"]');
            var blogPostTitle = blogPost.find('.o_blog_post_title').html() || '';
            var blogArticleLink = blogPost.find('.o_blog_post_title').parent('a').attr('href');
            if ($element.hasClass('o_twitter')) {
                url = 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=Amazing blog article : ' + blogPostTitle + "! " + window.location.host + blogArticleLink;
            } else if ($element.hasClass('o_facebook')) {
                url = 'https://www.facebook.com/sharer/sharer.php?u=' + window.location.host + blogArticleLink;
            } else if ($element.hasClass('o_linkedin')) {
                url = 'https://www.linkedin.com/shareArticle?mini=true&url=' + window.location.host + blogArticleLink + '&title=' + blogPostTitle;
            } else if ($element.hasClass('o_google')) {
                url = 'https://plus.google.com/share?url=' + window.location.host + blogArticleLink;
            }
        }
        window.open(url, '', 'menubar=no, width=500, height=400');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onYearCollapseClick: function (ev) {
        this._toggleYearCollapse($(ev.currentTarget));
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onBlogPostMouseEnter: function (ev) {
        $('div.o_blog_post_complete a').not('#' + ev.srcElement.id).addClass('unhover');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onBlogPostMouseLeave: function (ev) {
        $('div.o_blog_post_complete a').not('#' + ev.currentTarget.id).removeClass('unhover');
    },
});
});
