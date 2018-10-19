odoo.define('website_blog.website_blog', function (require) {
"use strict";

var sAnimations = require('website.content.snippets.animation');

sAnimations.registry.websiteBlog = sAnimations.Class.extend({
    selector: '.website_blog',
    read_events: {
        'click .cover_footer': '_onNextBlogClick',
        'click a[href^="#blog_content"]': '_onAnimate',
        'click .o_twitter, .o_facebook, .o_linkedin, .o_google, .o_twitter_complete, .o_facebook_complete, .o_linkedin_complete, .o_google_complete': '_onShareArticle',
        'click .blog_post_year_collapse': '_onToggleChevron',
        'mouseenter div.o_blog_post_complete a': '_onHoverBlogPost',
        'mouseleave div.o_blog_post_complete a': '_onUnhoverBlogPost'
    },

    /**
     * @override
     * @param {Object} parent
     */
    start: function (parent) {
        $(".js_tweet, .js_comment").share({});
        
        /* Collapse in active year */
        var $activeYear = $('.blog_post_year li.active');
        if ($activeYear.length) {
            var id = $activeYear.closest('ul').attr('id');
            $("li.blog_post_year_collapse[data-target='#"+ id +"']").click();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} ev
     */
    _onNextBlogClick: function (ev) {
        ev.preventDefault();
        var newLocation = $('.js_next')[0].href;
        var top = $('.cover_footer').offset().top;
        $('.cover_footer').animate({
            height: $(window).height()+'px'
        }, 300);
        $('html, body').animate({
            scrollTop: top
        }, 300, 'swing', function () {
           window.location.href = newLocation;
        });
    },
    /**
     * @private
     * @param {Object} ev
     */
    _onAnimate: function (ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        var element = ev.currentTarget;
        var target = $(element.hash);
        $('html, body').stop().animate({
            'scrollTop': target.offset().top - 32
        }, 500, 'swing', function () {
            window.location.hash = 'blog_content';
        });
    },
    /**
     * Sharing links hover in blogpost
     *
     * @private
     * @param {Object} ev
     */
    _onShareArticle: function (ev) {
        var url = '';
        var $element = $(ev.currentTarget);
        if ($element.is('*[class*="_complete"]')) {
            var blog_title_complete = $('#blog_post_name').html() || '';
            if ($element.hasClass('o_twitter_complete')){
                url = 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=Amazing blog article : '+blog_title_complete+"! Check it live: "+window.location.href;
            } else if ($element.hasClass('o_facebook_complete')){
                url = 'https://www.facebook.com/sharer/sharer.php?u='+window.location.href;
            } else if ($element.hasClass('o_linkedin_complete')){
                url = 'https://www.linkedin.com/shareArticle?mini=true&url='+window.location.href+'&title='+blog_title_complete;
            } else {
                url = 'https://plus.google.com/share?url='+window.location.href;
            }
        } else {
            var blog_post = $element.parents("[name='blog_post']");
            var blog_post_title = blog_post.find('.o_blog_post_title').html() || '';
            var blog_article_link = blog_post.find('.o_blog_post_title').parent('a').attr('href');
            if ($element.hasClass('o_twitter')) {
                url = 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=Amazing blog article : '+blog_post_title+"! "+window.location.host+blog_article_link;
            } else if ($element.hasClass('o_facebook')){
                url = 'https://www.facebook.com/sharer/sharer.php?u='+window.location.host+blog_article_link;
            } else if ($element.hasClass('o_linkedin')){
                url = 'https://www.linkedin.com/shareArticle?mini=true&url='+window.location.host+blog_article_link+'&title='+blog_post_title;
            } else if ($element.hasClass('o_google')){
                url = 'https://plus.google.com/share?url='+window.location.host+blog_article_link;
            }
        }
        window.open(url, "", "menubar=no, width=500, height=400");
    },
    /**
     * Archives years collapse
     *
     * @private
     * @param {Object} ev
     */
    _onToggleChevron: function (ev) {
        $(ev.currentTarget).find('i.fa').toggleClass('fa-chevron-down fa-chevron-right');
    },
    /**
     * @private
     * @param {Object} ev
     */
    _onHoverBlogPost: function (ev) {
        $('div.o_blog_post_complete a').not('#'+ev.srcElement.id).addClass('unhover');
    },
    /**
     * @private
     * @param {Object} ev
     */
    _onUnhoverBlogPost: function (ev) {
        $('div.o_blog_post_complete a').not('#'+ev.currentTarget.id).removeClass('unhover');
    },

});

});
