$(document).ready(function() {
    var discussion = false;
    var share = false;
    var top_nav = _.isNull($('#website-top-navbar-placeholder').height()) ? 0 : $('#website-top-navbar-placeholder').height();
    var vHeight = $(window).height() - ($('header').height() + top_nav);
    $('.cover_header').css('min-height', vHeight);
    function page_transist(event) {
        event.preventDefault();
        newLocation = $('.js_next')[0].href;
        $('.cover_footer')
        .fadeIn(900, newpage);
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

    //check custome options inline discussion and select to tweet(share) are checked.
    openerp.jsonRpc("/blogpsot/get_custom_options", 'call', {}).then(function(res){
        discussion = res['Allow comment in text'];
        share = res['Select to Tweet'];
        var content = $("#blog_content p");
        if(content.length && discussion){
            $('#discussions_wrapper').empty();
            new openerp.website.blog_discussion({'content' : content});
        }
        if (share) $("p,h1,h2,h3,h4,ul").share({'author_name':$('#blog_author').text()});
    });
    $('.cover_footer').on('click',page_transist);
    $('a[href^="#blog_content"]').on('click', animate);

    function page_upwards() {
        var translationValue = $("#wrap:last-child").get(0).getBoundingClientRect().top;
        $("#wrap:last-child").addClass('easing_upward');
        setTimeout(function(){
            $html = $(document.documentElement);
            $("#wrap:first-child").add($html).scrollTop(0);
            $("#wrap:last-child").removeClass('easing_upward');
            $("#wrap:first").remove();
            var content = $(document).find("#blog_content p");
            if (content && discussion){
               new openerp.website.blog_discussion({'content' : content});
            }
        }, 500 );
    }

    function newpage() {
        $.ajax({
            url: newLocation
        }).done(function(data) {
            $('main').append($(data).find('main').html());
            page_upwards();
            //bind again it takes control from now on, until page relaod.
            $(document).find('.cover_footer').on('click',page_transist);
            $(document).find('.cover_header').css('min-height', vHeight);
            $(document).find('a[href^="#blog_content"]').on('click', animate);
            if (share) $("p,h1,h2,h3,h4,ul").share({'author_name':$(data).find('#blog_author').text()});
            if (newLocation != window.location)
                history.pushState(null, null, newLocation);
        });
    }
});
