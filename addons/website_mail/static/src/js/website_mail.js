$(document).ready(function () {

    $(document).on('click', '.js_follow_btn, .js_unfollow_btn', function (ev) {
        ev.preventDefault();

        var self = this;
        var $data = $(this).parents("div.js_follow");
        var $email = $data.find(".js_follow_email");
        var message_is_follower = $data.attr("data-follow") || "off";
        $data.attr("data-follow", message_is_follower == 'off' ? 'on' : 'off');

        openerp.jsonRpc('/website_mail/follow', 'call', {
            'id': $data.data('id'),
            'object': $data.data('object'),
            'message_is_follower': message_is_follower,
            'email': $email && $email.val() || false,
        }).then(function (result) {
            if (result) {
                $data.find(" > *").toggleClass("hidden");
            }
            $data.attr("data-follow", result ? 'on' : 'off');
        });
    });

});
