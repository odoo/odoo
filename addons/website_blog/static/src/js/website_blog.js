$(document).ready(function() {
    var discussion = false;
    var share = false;

    function updateMinHeight(event) {
        var vHeight = $(window).height();
        $(document).find('.cover_header').css('min-height', vHeight);
    }

    function page_transist(event) {
        event.preventDefault();
        newLocation = $('.js_next')[0].href;
        var top = $('.cover_footer').offset().top;
        $('.cover_footer').animate({
            height: $(window).height()+'px'
        }, 500);
        $('html, body').animate({
            scrollTop: top
        }, 500, 'swing', function() {
           window.location.href = newLocation;
        });
    }

    function animate(event) {
        event.stopImmediatePropagation();
        var target = this.hash;
        $target = $(target);
        $('html, body').stop().animate({
            'scrollTop': $target.offset().top
        }, 900, 'swing', function () {
            window.location.hash = target;
        });
    }
    $( window ).on('resize', function() {
        updateMinHeight();
    });
    //check custome options inline discussion and select to tweet(share) are checked.
    openerp.jsonRpc("/blogpsot/get_custom_options", 'call', {}).then(function(res){
        discussion = res['Allow comment in text'];
        share = res['Select to Tweet'];
        var content = $("#blog_content p");
        if(content.length && discussion){
            $('#discussions_wrapper').empty();
            new openerp.website.blog_discussion({'content' : content});
        }
        if (share) $("h1, h2, h3, h4, ul, p","#blog_content ,.blog_title").share({'author_name':$('#blog_author').text()});
    });
    $('.cover_footer').on('click',page_transist);
    $('a[href^="#blog_content"]').on('click', animate);
    updateMinHeight();
});
