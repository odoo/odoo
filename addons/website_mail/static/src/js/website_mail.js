$(document).ready(function () {

    /* ----- FOLLOWING STUFF ---- */
    $('[data-follow]:has([data-follow])').each(function () {
        var $pub = $("[data-follow]", this);
        if($pub.size())
            $(this).attr("data-follow", $pub.attr("data-follow"));
        else
            $(this).removeAttr("data-follow");
    });

    $(document).on('click', '.js_follow', function (ev) {
        console.log(ev);
        ev.preventDefault();
        var $data = $(":first", this).parents("[data-follow]");
        var message_is_follower = $data.first().attr("data-follow");
        $data.attr("data-follow", message_is_follower == 'off' ? 'on' : 'off');
        $.post('/website_mail/follow', {
            'id': $(this).data('id'),
            'object': $(this).data('object'),
            'message_is_follower': message_is_follower,
        }, function (result) {
            $data.attr("data-follow", + result ? 'on' : 'off');
        });
    });

});
