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
        var check = true;
        $form.find(".control-group").removeClass("error");
        $form.find("textarea,input").each(function() {
            if ($(this).val().length < 3) {
                $(this).parents(".control-group:first").addClass("error");
                check = false;
            }
        });
        if (!check) return false;
        $form.css("visibility", "hidden");
    });
});