odoo.define('website_blog.website_blog', function (require) {
"use strict";

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

function shareArticle(event){
    var url = '';
    if ($(this).is('*[class*="_complete"]')) {
        var blog_title_complete = $('#blog_post_name').html() || '';
        if ($(this).hasClass('o_twitter_complete')){
            url = 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=Amazing blog article : '+blog_title_complete+"! Check it live: "+window.location.href;
        } else if ($(this).hasClass('o_facebook_complete')){
            url = 'https://www.facebook.com/sharer/sharer.php?u='+window.location.href;
        } else if ($(this).hasClass('o_linkedin_complete')){
            url = 'https://www.linkedin.com/shareArticle?mini=true&url='+window.location.href+'&title='+blog_title_complete;
        } else {
            url = 'https://plus.google.com/share?url='+window.location.href;
        }
    }
    else {
        var blog_post = $(this).parents("[name='blog_post']");
        var blog_post_title = blog_post.find('.o_blog_post_title').html() || '';
        var blog_article_link = blog_post.find('.o_blog_post_title').parent('a').attr('href');
        if ($(this).hasClass('o_twitter')) {
            url = 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=Amazing blog article : '+blog_post_title+"! "+window.location.host+blog_article_link;
        } else if ($(this).hasClass('o_facebook')){
            url = 'https://www.facebook.com/sharer/sharer.php?u='+window.location.host+blog_article_link;
        } else if ($(this).hasClass('o_linkedin')){
            url = 'https://www.linkedin.com/shareArticle?mini=true&url='+window.location.host+blog_article_link+'&title='+blog_post_title;
        } else if ($(this).hasClass('o_google')){
            url = 'https://plus.google.com/share?url='+window.location.host+blog_article_link;
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
        /* Collapse in active tag or latest year */
        var $activeYear = $('.blog_post_year li.active');
        if ($activeYear.length) {
            $activeYear.closest('ul').addClass('in').prev().find('i.fa').toggleClass('fa-chevron-down fa-chevron-right');
        }

        $('#o_blog_tag_collapse').on('click', '.fa-chevron-right',function(){
            $(this).parents('li').find('ul:first').show('normal');
            $(this).toggleClass('fa-chevron-right fa-chevron-down');
        });

        $('#o_blog_tag_collapse').on('click', '.fa-chevron-down',function(){
            $(this).parent().find('ul:first').hide('normal');
            $(this).toggleClass(' fa-chevron-right fa-chevron-down');
        });

        var $activeBlogTag = $('#o_blog_tag_collapse li.active');
        if ($activeBlogTag.length) {
            $activeBlogTag.parentsUntil("#o_blog_tag_collapse").find('i.fa').click()
        }

    }

    /* Sharing links hover in blogpost */
    $('div.o_blog_post_complete a').hover(
        function() { $('div.o_blog_post_complete a').not('#'+this.id).addClass('unhover'); },
        function() { $('div.o_blog_post_complete a').not('#'+this.id).removeClass('unhover'); }
    );
});

});
