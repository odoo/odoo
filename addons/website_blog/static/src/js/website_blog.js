$(document).ready(function() {
    if ($('.website_blog').length) {
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
                window.location.hash = 'blog_content';
            });
        }

        var content = $("div[enable_chatter_discuss='True']").find('p[data-chatter-id]');
        if (content) {
            openerp.jsonRpc("/blog/get_user/", 'call', {}).then(function(data){
                $('#discussions_wrapper').empty();
                new openerp.website.blog_discussion({'content' : content, 'public_user':data[0]});
            });
        }

        $('.js_fullheight').css('min-height', $(window).height());
        $(".js_tweet").share({'author_name':$('#blog_author').text()});
        $('.cover_footer').on('click',page_transist);
        $('a[href^="#blog_content"]').on('click', animate);
    }

    $('.share_content a').on('click', function() {
        var url = $(this).parent().attr('data-url');
        var text_to_share = $(this).parent().attr('data-content');
        var social_network = {
            'facebook':'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url),
            'twitter': 'https://twitter.com/intent/tweet?original_referer=' + encodeURIComponent(url) + '&amp;text=' + encodeURIComponent(text_to_share + ' - ' + url),
            'linkedin': 'https://www.linkedin.com/shareArticle?mini=true&url=' + encodeURIComponent(url) + '&title=' + encodeURIComponent(text_to_share) + '&summary=' + encodeURIComponent($(this).parent().attr('data-description')),
            'google-plus': 'https://plus.google.com/share?url=' + encodeURIComponent(url)
        };
        if (_.contains(_.keys(social_network),  $(this).attr('data-social'))){
            var window_height = 500, window_width = 500, left = (screen.width/2)-(window_width/2), top = (screen.height/2)-(window_height/2);
            window.open(social_network[$(this).attr('data-social')], '', 'menubar=no, toolbar=no, resizable=yes, scrollbar=yes, height=' + window_height + ',width=' + window_width + ', top=' + top + ', left=' + left);
        }
    });
});
