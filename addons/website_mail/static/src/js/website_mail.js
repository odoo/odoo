(function () {
    'use strict';

    var website = openerp.website;

    website.snippet.animationRegistry.follow = website.snippet.Animation.extend({
        selector: ".js_follow",
        start: function (editable_mode) {
            var self = this;
            this.is_user = false;

            openerp.jsonRpc('/website_mail/is_follower', 'call', {
                model: this.$target.data('object'),
                id: this.$target.data('id'),
                fields: ['name', 'alias_id'],
            }).always(function (data) {
                self.is_user = data.is_user;
                self.$target.find('.js_mg_email').attr('href', 'mailto:' + data.alias_id[1]);
                self.$target.find('.js_mg_link').attr('href', '/groups/' + data.id);
                self.toggle_subscription(data.is_follower);
                self.$target.find('input.js_follow_email')
                    .val(data.email ? data.email : "")
                    .attr("disabled", data.is_follower || (data.email.length && self.is_user) ? "disabled" : false);
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
            return;
        },
        on_click: function () {
            var self = this;
            var $email = this.$target.find(".js_follow_email");

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
                self.toggle_subscription(follow);
            });
        },
        toggle_subscription: function(follow) {
            if (follow) {
                this.$target.find(".js_mg_follow_form").addClass("hidden");
                this.$target.find(".js_mg_details").removeClass("hidden");
            }
            else {
                this.$target.find(".js_mg_follow_form").removeClass("hidden");
                this.$target.find(".js_mg_details").addClass("hidden");
            }
            this.$target.find('input.js_follow_email').attr("disabled", follow || this.is_user ? "disabled" : false);
            this.$target.attr("data-follow", follow ? 'on' : 'off');
        },
    });

    $(document).ready(function () {
        $('.js_follow_btn').on('click', function (ev) {
            var email = $(ev.currentTarget).parents('.js_mg_follow_form').first().find('.js_follow_email').val();
            $(document).find('.js_follow_email').val(email);
        });
    });
})();
