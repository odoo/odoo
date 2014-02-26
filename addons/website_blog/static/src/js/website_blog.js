$(document).ready(function() {
    var discussion = false;
    var share = false;
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

    function arrow_scroll(){
        var node = $('#blog_angle_down');
        var stickyTop = node.offset().top - 50;
        $(window).scroll(function(event){
            var scrolltop = $(window).scrollTop();
            if (stickyTop > scrolltop)
                node.stop().animate({"marginTop": ($(window).scrollTop() - 50) + "px"}, "slow" );
        });
    }

    //check custome options inline discussion and select to tweet(share) are checked.
    openerp.jsonRpc("/blogpsot/get_custom_options", 'call', {}).then(function(res){
        discussion = res['Inline Discussion'];
        share = res['Select to Tweet'];
        var content = $("#blog_content p");
        if(content.length && discussion){
            $('#discussions_wrapper').empty();
            new openerp.website.blog_discussion({'content' : content});
        }
        if (share) $("p").share();
    });
    $('.cover_footer').on('click',page_transist);
    $('a[href^="#blog_content"]').on('click', animate);
    arrow_scroll();

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
           arrow_scroll();
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
            $(document).find('a[href^="#blog_content"]').on('click', animate);
            if (share) $("p").share();
            if (newLocation != window.location)
                history.pushState(null, null, newLocation);
        });
    }
});
