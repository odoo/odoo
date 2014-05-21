(function () {
    'use strict';

    var website = openerp.website;

    website.snippet.animationRegistry.follow = website.snippet.Animation.extend({
        selector: ".js_follow",
        start: function (editable_mode) {
            var self = this;

            // set value and display button
            self.$target.find("input").removeClass("hidden");
            openerp.jsonRpc('/website_mail/is_follower', 'call', {
                model: this.$target.data('object'),
                id: +this.$target.data('id'),
            }).always(function (data) {
                self.$target.find('input.js_follow_email')
                    .val(data.email ? data.email : "")
                    .attr("disabled", data.is_follower && data.email.length ? "disabled" : false);
                self.$target.attr("data-follow", data.is_follower ? 'on' : 'off');
                self.$target.removeClass("hidden");
            });

            // not if editable mode to allow designer to edit alert field
            if (!editable_mode) {
                $('.js_follow > .alert').addClass("hidden");
                $('.js_follow > .input-group-btn.hidden').removeClass("hidden");
                this.$target.find('.js_follow_btn, .js_unfollow_btn').on('click', function (event) {
                    event.preventDefault();
                    self.on_click();
                });
            }
        },
        on_click: function () {
            var self = this;
            var $email = this.$target.find(".js_follow_email:visible");

            if ($email.length && !$email.val().match(/.+@.+/)) {
                this.$target.addClass('has-error');
                return false;
            }
            this.$target.removeClass('has-error');

            openerp.jsonRpc('/website_mail/follow', 'call', {
                'id': +this.$target.data('id'),
                'object': this.$target.data('object'),
                'message_is_follower': this.$target.attr("data-follow") || "off",
                'email': $email.length ? $email.val() : false,
            }).then(function (follow) {
                if (follow) {
                    self.$target.find(".js_follow_email, .input-group-btn").addClass("hidden");
                    self.$target.find(".alert").removeClass("hidden");
                }
                self.$target.find('input.js_follow_email').attr("disabled", follow ? "disabled" : false);
                self.$target.attr("data-follow", follow ? 'on' : 'off');
            });
        },
    });
})();
