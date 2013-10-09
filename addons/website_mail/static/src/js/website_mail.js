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
        ev.preventDefault();
        var $data = $(":first", this).parents("[data-follow]");
        var $email = $data.first().siblings(".js_follow_email");
        var message_is_follower = $data.first().attr("data-follow");
        $data.attr("data-follow", message_is_follower == 'off' ? 'on' : 'off');
        openerp.jsonRpc('/website_mail/follow', 'call', {
            'id': $(this).data('id'),
            'object': $(this).data('object'),
            'message_is_follower': message_is_follower,
            'email': $email && $email.val() || false,
        }).then(function (result) {
            $data.attr("data-follow", + result ? 'on' : 'off');
        });
    });

});
