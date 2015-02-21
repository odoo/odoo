$(document).ready(function() {
    if ($('.website_portal').length) {
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
        function animate(event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            var target = $(this.hash);
            $('html, body').stop().animate({
                'scrollTop': target.offset().top - 32
            }, 500, 'swing', function () {
                window.location.hash = 'portal_content';
            });
        }

        var content = $("div[enable_chatter_discuss='True']").find('p[data-chatter-id]');
        if (content) {
            openerp.jsonRpc("/portal/get_user/", 'call', {}).then(function(data){
                $('#discussions_wrapper').empty();
                new openerp.website.portal_discussion({'content' : content, 'public_user':data[0]});
            });
        }

        $('.js_fullheight').css('min-height', $(window).height());
        $(".js_tweet").share({'author_name':$('#portal_author').text()});
        $('.cover_footer').on('click',page_transist);
        $('a[href^="#portal_content"]').on('click', animate);
    }

});
