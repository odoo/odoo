$(document).ready(function () {
    $('.js_website_mail').on('click', '.js_publish', function (e) {
        var $link = $(e.currentTarget);
        var $media = $link.parent();
        $media.toggleClass('css_published');
        $.post('/blog/publish/', {'message_id': $link.data('id')}, function (result) {
            if (+result) $media.addClass('css_published');
            else $media.removeClass('css_published');
        });
        return false;
    });

    $form = $('.js_website_mail form#post');
    $form.submit(function (e) {
        var error = $form.find("textarea").val().length < 3;
        $form.find("textarea").toggleClass("has-error", error);
        if (!error) {
            $form.css("visibility", "hidden");
            $.post(window.location.pathname + '/post', {'body': $form.find("textarea").val()}, function (url) {
                window.location.href = url
            });
        }
        return false;
    });
});