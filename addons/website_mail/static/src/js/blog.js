$(document).ready(function () {
    $('.js_website_mail').on('click', '.js_publish', function (e) {
        e.preventDefault();
        var $media = $(this).parent();
        $media.toggleClass('css_published');
        $.post('/blog/publish/', {'message_id': $(this).data('id')}, function (result) {
            if (+result) $media.addClass('css_published');
            else $media.removeClass('css_published');
        });
    });

    $form = $('.js_nav_year a:first').on('click', function (e) {
        e.preventDefault();
        $(this).next("ul").toggle();
    });

    $form = $('.js_nav_month a:first').on('click', function (e) {
        e.preventDefault();
        var $ul = $(this).next("ul");
        if (!$ul.find('li').length) {
            $.post('/blog/nav', {'domain': $(this).data("domain")}, function (result) {
                var result = JSON.parse(result);
                var blog_id = +window.location.pathname.split("/").pop();
                $(result).each(function () {
                    var $a = $('<a href="/blog/'+this.res_id+'/'+this.id+'"/>').text(this.subject);
                    var $li = $("<li/>").append($a);
                    if (blog_id == this.id)
                        $li.addClass("active");
                    if (!this.website_published)
                        $a.css("color", "red");
                    $ul.append($li);
                });

            });
        } else {
            $ul.toggle();
        }
    });

    $form = $('.js_website_mail form#post');
    $form.submit(function (e) {
        e.preventDefault();
        var error = $form.find("textarea").val().length < 3;
        $form.find("textarea").toggleClass("has-error", error);
        if (!error) {
            $form.css("visibility", "hidden");
            $.post(window.location.pathname + '/post', {'body': $form.find("textarea").val()}, function (url) {
                window.location.href = url
            });
        }
    });
});