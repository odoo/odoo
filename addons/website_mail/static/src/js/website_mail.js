$(document).ready(function () {

    $(document).on('click', '.js_follow_btn', function (ev) {
        ev.preventDefault();

	var self = this;
        var $data = $(this).parents("div.js_follow");
        var $email = $(".js_follow_email", $data);
        var message_is_follower = $data.attr("data-follow");
        $data.attr("data-follow", message_is_follower == 'off' ? 'on' : 'off');

        openerp.jsonRpc('/website_mail/follow', 'call', {
            'id': $data.data('id'),
            'object': $data.data('object'),
            'message_is_follower': message_is_follower,
            'email': $email && $email.val() || false,
        }).then(function (result) {
	    if (result) {
	        $data.html('<div class="alert alert-success mb0">Thanks for your subscription!</div>')
	    } else {
                $data.attr("data-follow", + result ? 'on' : 'off');
	        $(self).text('Subscribe')
	    }
        });
    });

});
