$(document).ready(function() {

    $("#blog_content p").inlineDisqussions(); //Allow inline comments on blog post

    $('.cover_footer').click(function(event) {
        event.preventDefault();
        var translationValue  = $('.cover_footer').get(0).getBoundingClientRect().top;
        newLocation = $(this).find('.js_next')[0].href;
        $('.blog_cover').addClass('page_fadeup_out');
      
      $('.cover_footer')
        .addClass('page_upward')
        .css({ "transform": "translate3d(0, -"+ translationValue +"px, 0)" })
        .fadeIn(10000, newpage);
    });
    function newpage() {
        $.ajax({
          url: newLocation,
        }).done(function(data) {
           document.getElementsByTagName('html')[0].innerHTML = data;
           if (newLocation != window.location) {
                history.pushState(null, null, newLocation);
            }
        });
    }

    $(document).on('mouseover',function() {
        $('.cover_footer').click(function(event) {
            event.preventDefault();
            var translationValue  = $('.cover_footer').get(0).getBoundingClientRect().top;
            newLocation = $(this).find('.js_next')[0].href;
            $('.blog_cover').addClass('page_fadeup_out');
          
          $('.cover_footer')
            .addClass('page_upward')
            .css({ "transform": "translate3d(0, -"+ translationValue +"px, 0)" })
            .fadeIn(900, newpage);
          $("html, body").stop().animate({ scrollTop:  $("#wrap").offset().top }, 'slow', 'swing');
        });
        
        $('a[href^="#"]').on('click',function (e) {
            e.preventDefault();
        
            var target = this.hash,
            $target = $(target);
        
            $('html, body').stop().animate({
                'scrollTop': $target.offset().top
            }, 900, 'swing', function () {
                window.location.hash = target;
            });
        });
    });
});
