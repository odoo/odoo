$(document).ready(function() {
    $("#blog_content p").inlineDisqussions({'document_user': $('#is_document_user').length}); //Allow inline comments on blog post
    $('.cover_footer').on('click',page_transist);
    $('a[href^="#blog_content"]').on('click', animate);
    $("p").share();
    function page_transist(event) {
        event.preventDefault();
        var translationValue  = $('.cover_footer').get(0).getBoundingClientRect().top;
        newLocation = $('.js_next')[0].href;
        $('.cover_footer')
        .fadeIn(900, newpage);
    }

    function animate(event) {
       event.stopImmediatePropagation()
        var target = this.hash,
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
           });
           if (newLocation != window.location) {
                history.pushState(null, null, newLocation);
            }
            //bind again it takes control from now on, until page relaod.
            $(document).find('.cover_footer').on('click',page_transist);
            $(document).find('a[href^="#blog_content"]').on('click', animate);
            $(document).find("#blog_content p").inlineDisqussions({'document_user': $('#is_document_user').length});
            $("p").share();
        });
    }
});
