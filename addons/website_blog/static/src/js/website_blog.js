$(document).ready(function() {
    var discussion = false;
    var share = false;

    var def = $.Deferred();
    openerp.jsonRpc("/blogpsot/get_custom_options", 'call', {
    }).then(function(res){
        discussion = res['Inline Discussion']
        share = res['Select to Tweet']
        return def.resolve()
    })
    def.done( function(){
        var content = $("#blog_content p");
        if(content.length && discussion)
            new openerp.website.blog_discussion({'content' : content});
        if (share) $("p").share();
    })
    $('.cover_footer').on('click',page_transist);
    $('a[href^="#blog_content"]').on('click', animate);

    function page_transist(event) {
        event.preventDefault();
        var translationValue  = $('.cover_footer').get(0).getBoundingClientRect().top;
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

    function newpage() {
        $.ajax({
          url: newLocation,
        }).done(function(data) {
           $('main').append($(data).find('main').html());
           $("html").stop().animate({ scrollTop: $("#wrap:last-child").offset().top }, 1000,function(e){
               $("#wrap:first").remove();
               $(document).scrollTop($("#wrap:last-child").offset().top);
               //bind again it takes control from now on, until page relaod.
               $(document).find('.cover_footer').on('click',page_transist);
               $(document).find('a[href^="#blog_content"]').on('click', animate);
               var content = $(document).find("#blog_content p");
               if (content && discussion)
                   new openerp.website.blog_discussion({'content' : content});
               if (share) $("p").share();
           });
            if (newLocation != window.location) {
                history.pushState(null, null, newLocation);
            }
        });
    }
});
