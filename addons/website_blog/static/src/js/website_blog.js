$(document).ready(function() {

    function page_transist(event) {
        event.preventDefault();
        newLocation = $('.js_next')[0].href;
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

    function animate() {
        var target = $(this.hash);
        $('html, body').stop().animate({
            'scrollTop': target.offset().top - 32
        }, 500, 'swing', function () {
            window.location.hash = 'blog_content';
        });
        return false;
    }

    var content = $(".js_discuss");
    if(content){
        $('#discussions_wrapper').empty();
        new openerp.website.blog_discussion({'content' : content});
    }

    $('.js_header').css('min-height', $(window).height());
    $(".js_tweet").find("h1, h2, h3, h4, li, p").share({'author_name':$('#blog_author').text()});
    $('.cover_footer').on('click',page_transist);
    $('a[href^="#blog_content"]').on('click', animate);

});
