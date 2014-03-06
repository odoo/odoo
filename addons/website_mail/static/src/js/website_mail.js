(function () {
    'use strict';

    var website = openerp.website;

    website.snippet.animationRegistry.follow = website.snippet.Animation.extend({
        selector: ".js_follow",
        start: function () {
            var self = this;

            openerp.jsonRpc('/website_mail/is_follower/', 'call', {
                model: this.$target.data('object'),
                id: +this.$target.data('id'),
            }).always(function (data) {
                self.$target.find('input.js_follow_email')
                    .val(data.email ? data.email : "")
                    .attr("disabled", data.email.length ? "disabled" : false);
                self.$target.attr("data-follow", data.is_follower ? 'on' : 'off');
                self.$target.removeClass("hidden");
            });
        },
    });
})();

$(document).ready(function () {

    $('.js_follow > .alert').addClass("hidden");
    $('.js_follow > .input-group-btn.hidden').removeClass("hidden");

    $('.js_follow_btn, .js_unfollow_btn').on('click', function (ev) {
        ev.preventDefault();

        var $follow = $(this).parents("div.js_follow");
        var $email = $follow.find(".js_follow_email:visible");

        if ($email.length && !$email.val().match(/.+@.+/)) {
            $follow.addClass('has-error');
            return false;
        }

        $email.removeClass('has-error');

        var message_is_follower = $follow.attr("data-follow") || "off";
        $follow.attr("data-follow", message_is_follower == 'off' ? 'on' : 'off');

        openerp.jsonRpc('/website_mail/follow', 'call', {
            'id': +$follow.data('id'),
            'object': $follow.data('object'),
            'message_is_follower': message_is_follower,
            'email': $email.length ? $email.val() : false,
        }).then(function (follow) {
            if (follow) {
                $follow.find(" > *").toggleClass("hidden");
            }
            $follow.attr("data-follow", follow ? 'on' : 'off');
        });
    });
});
