odoo.define('website_blog.website_blog', function (require) {
"use strict";
var core = require('web.core');

function page_transist(event) {
    event.preventDefault();
    var newLocation = $('.js_next')[0].href;
    var top = $('.cover_footer').offset().top;
    $('.cover_footer').animate({
        height: $(window).height()+'px'
    }, 300);
    $('html, body').animate({
        scrollTop: top
    }, 300, 'swing', function() {
       window.location.href = newLocation;
    });
}
function animate(event) {
    event.preventDefault();
    event.stopImmediatePropagation();
    var target = $(this.hash);
    $('html, body').stop().animate({
        'scrollTop': target.offset().top - 32
    }, 500, 'swing', function () {
        window.location.hash = 'blog_content';
    });
}

function shareArticle(event) {
    var url = '';
    var articleURL;
    var twitterText = core._t("Amazing blog article : %s! Check it live: %s");
    if ($(this).is('*[class*="_complete"]')) {
        var blog_title_complete = encodeURIComponent($('#blog_post_name').html() || '');
        articleURL = encodeURIComponent(window.location.href);
        if ($(this).hasClass('o_twitter_complete')){
            var tweetText = _.string.sprintf(twitterText, blog_title_complete, articleURL);
            url = 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=' + tweetText;
        } else if ($(this).hasClass('o_facebook_complete')){
            url = 'https://www.facebook.com/sharer/sharer.php?u=' + articleURL;
        } else if ($(this).hasClass('o_linkedin_complete')){
            url = 'https://www.linkedin.com/shareArticle?mini=true&url=' + articleURL + '&title=' + blog_title_complete;
        } else {
            url = 'https://plus.google.com/share?url=' + articleURL;
        }
    }
    else {
        var blog_post = $(this).parents("[name='blog_post']");
        var blog_post_title = encodeURIComponent(blog_post.find('.o_blog_post_title').html() || '');
        var blog_article_link = blog_post.find('.o_blog_post_title').parent('a').attr('href');
        articleURL = encodeURIComponent(window.location.host + blog_article_link);
        if ($(this).hasClass('o_twitter')) {
            var tweetText = _.string.sprintf(twitterText, blog_post_title, articleURL);
            url = 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=' + tweetText;
        } else if ($(this).hasClass('o_facebook')){
            url = 'https://www.facebook.com/sharer/sharer.php?u=' + articleURL;
        } else if ($(this).hasClass('o_linkedin')){
            url = 'https://www.linkedin.com/shareArticle?mini=true&url=' + articleURL + '&title=' + blog_post_title;
        } else if ($(this).hasClass('o_google')){
            url = 'https://plus.google.com/share?url=' + articleURL;
        }
    }
    window.open(url, "", "menubar=no, width=500, height=400");
}

$(document).ready(function() {
    if ($('.website_blog').length) {
        $(".js_tweet, .js_comment").share({});
        $('.cover_footer').on('click', page_transist);
        $('a[href^="#blog_content"]').on('click', animate);
        $('.o_twitter, .o_facebook, .o_linkedin, .o_google, .o_twitter_complete, .o_facebook_complete, .o_linkedin_complete, .o_google_complete').on('click', shareArticle);
        /* Archives years collapse */
        $('.blog_post_year_collapse').on('click', function() {
            $(this).find('i.fa').toggleClass('fa-chevron-down fa-chevron-right');
        });
        /* Collapse in active year */
        var $activeYear = $('.blog_post_year li.active');
        if ($activeYear.length) {
            var id = $activeYear.closest('ul').attr('id');
            $("li.blog_post_year_collapse[data-target='#"+ id +"']").click();
        }
    }

    /* Sharing links hover in blogpost */
    $('div.o_blog_post_complete a').hover(
        function() { $('div.o_blog_post_complete a').not('#'+this.id).addClass('unhover'); },
        function() { $('div.o_blog_post_complete a').not('#'+this.id).removeClass('unhover'); }
    );
});

});
