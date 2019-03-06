odoo.define('website_mail.follow', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.follow = publicWidget.Widget.extend({
    selector: '.js_follow',
    disabledInEditableMode: false,

    start: function () {
        var self = this;
        this.is_user = false;

        var always = function (data) {
            self.is_user = data.is_user;
            self.email = data.email;
            self.toggle_subscription(data.is_follower, data.email);
            self.$target.removeClass('d-none');
        };

        this._rpc({
            route: '/website_mail/is_follower',
            params: {
                model: this.$target.data('object'),
                res_id: this.$target.data('id'),
            },
        }).then(always).guardedCatch(always);

        // not if editable mode to allow designer to edit
        if (!this.editableMode) {
            $('.js_follow > .input-group-append.d-none').removeClass('d-none');
            this.$target.find('.js_follow_btn, .js_unfollow_btn').on('click', function (event) {
                event.preventDefault();
                self._onClick();
            });
        }
        return this._super.apply(this, arguments);
    },
    _onClick: function () {
        var self = this;
        var $email = this.$target.find(".js_follow_email");

        if ($email.length && !$email.val().match(/.+@.+/)) {
            this.$target.addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
            return false;
        }
        this.$target.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');

        var email = $email.length ? $email.val() : false;
        if (email || this.is_user) {
            this._rpc({
                route: '/website_mail/follow',
                params: {
                    'id': +this.$target.data('id'),
                    'object': this.$target.data('object'),
                    'message_is_follower': this.$target.attr("data-follow") || "off",
                    'email': email,
                },
            }).then(function (follow) {
                self.toggle_subscription(follow, email);
            });
        }
    },
    toggle_subscription: function (follow, email) {
        follow = follow || (!email && this.$target.attr('data-unsubscribe'));
        if (follow) {
            this.$target.find(".js_follow_btn").addClass('d-none');
            this.$target.find(".js_unfollow_btn").removeClass('d-none');
        }
        else {
            this.$target.find(".js_follow_btn").removeClass('d-none');
            this.$target.find(".js_unfollow_btn").addClass('d-none');
        }
        this.$target.find('input.js_follow_email')
            .val(email || "")
            .attr("disabled", email && (follow || this.is_user) ? "disabled" : false);
        this.$target.attr("data-follow", follow ? 'on' : 'off');
    },
});
});
