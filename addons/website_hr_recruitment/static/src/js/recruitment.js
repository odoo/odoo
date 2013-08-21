$(function () {
    $(document).on('click', '.js_published, .js_unpublished', function (e) {
        e.preventDefault();
        var $link = $(this).parent();
        $link.find('.js_published, .js_unpublished').addClass("hidden");
        var $unp = $link.find(".js_unpublished");
        var $p = $link.find(".js_published");
        $.post('/recruitment/published', {'id': $link.data('id'), 'object': $link.data('object')}, function (result) {
            if (+result) {
                $p.addClass("hidden");
                $unp.removeClass("hidden");
            } else {
                $p.removeClass("hidden");
                $unp.addClass("hidden");
            }
        });
    });
});
